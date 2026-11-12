"""Approval management and explicit operator-only administrator bootstrap."""
import argparse
import uuid
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, String, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from .accounts import User, admin_user, now, aware, user_view
from .database import Base, database, engine

router=APIRouter()

class AccessAudit(Base):
    __tablename__='access_audit'
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    actor_id: Mapped[str|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'),nullable=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'))
    action: Mapped[str]=mapped_column(String(30))
    image_limit: Mapped[int]
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))

class AccessChange(BaseModel):
    model_config={'extra':'forbid'}
    revision: int=Field(ge=1,strict=True)
    status: Literal['approved','pending','suspended']
    image_limit: int=Field(ge=0,le=100,strict=True)

def view(row):
    return {**user_view(row),'email':row.email,'revision':row.access_revision,
            'requested_at':aware(row.requested_at).isoformat() if row.requested_at else None}

@router.get('/admin/users')
def users(status:Literal['pending','approved','suspended']='pending',offset:int=0,user:User=Depends(admin_user),db:Session=Depends(database)):
    if offset<0:
        raise HTTPException(422,'Choose a valid page.')
    query=select(User).where(User.is_admin==False,User.access_status==status)
    rows=db.scalars(query.order_by(User.requested_at,User.id).offset(offset).limit(50)).all()
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    return {'users':[view(row) for row in rows],'total':total,'has_more':offset+len(rows)<total}

@router.put('/admin/users/{id}/access')
def change(id:str,values:AccessChange,user:User=Depends(admin_user),db:Session=Depends(database)):
    row=db.scalar(select(User).where(User.id==id).with_for_update())
    if not row:
        raise HTTPException(404,'Account not found.')
    if row.is_admin:
        raise HTTPException(409,'Administrator access is managed by the server operator.')
    if row.access_revision!=values.revision:
        raise HTTPException(409,'This account changed. Refresh and review it again.')
    if values.image_limit<row.image_requests_used:
        raise HTTPException(422,'Total allowance cannot be below requests already used. Set it equal to usage to leave zero requests remaining.')
    row.access_status=values.status;row.image_limit=values.image_limit;row.access_revision+=1
    db.add(AccessAudit(id=str(uuid.uuid4()),actor_id=user.id,user_id=row.id,action=values.status,image_limit=row.image_limit,created_at=now()))
    db.commit();return view(row)

def bootstrap(db,username):
    row=db.scalar(select(User).where(User.username==username.strip().lower()).with_for_update())
    if not row:
        raise ValueError('Account not found. Join the waitlist with your own account first.')
    if not row.is_admin:
        row.is_admin=True;row.access_status='approved';row.access_revision+=1
        db.add(AccessAudit(id=str(uuid.uuid4()),actor_id=None,user_id=row.id,action='bootstrap_admin',image_limit=row.image_limit,created_at=now()))
        db.commit()
    return row

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Explicitly enable administrator access for an existing account.')
    parser.add_argument('command',choices=['bootstrap'])
    parser.add_argument('--username',required=True)
    args=parser.parse_args()
    with Session(engine()) as db:
        try:
            bootstrap(db,args.username)
        except ValueError as exc:
            parser.exit(1,str(exc)+'\n')
    print('Administrator access enabled for the specified account. Sign in again or refresh access status.')
