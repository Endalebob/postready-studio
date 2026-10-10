import io
import os
from functools import lru_cache
from minio import Minio
from minio.error import S3Error

BUCKET = 'postready-private'


@lru_cache
def storage():
    return Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'],
                 secret_key=os.environ['MINIO_SECRET_KEY'], secure=os.getenv('MINIO_SECURE', 'false') == 'true')


def put(key, data):
    client = storage()
    if not client.bucket_exists(BUCKET):
        try:
            client.make_bucket(BUCKET)
        except S3Error as exc:
            if exc.code not in ('BucketAlreadyOwnedByYou', 'BucketAlreadyExists'):
                raise
    client.put_object(BUCKET, key, io.BytesIO(data), len(data), content_type='image/png')


def get(key):
    response = storage().get_object(BUCKET, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def remove(key):
    storage().remove_object(BUCKET, key)
