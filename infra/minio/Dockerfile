FROM golang:1.24.8 AS build
RUN CGO_ENABLED=0 go install github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z
FROM debian:bookworm-slim
COPY --from=build /go/bin/minio /usr/local/bin/minio
ENTRYPOINT ["minio"]
