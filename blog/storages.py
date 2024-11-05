# Custom storage classes
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class StaticStorage(S3Boto3Storage):
    bucket_name = settings.AWS_STATIC_BUCKET_NAME
    default_acl = 'public-read'
    custom_domain = settings.AWS_S3_CUSTOM_DOMAIN
    endpoint_url = settings.AWS_S3_ENDPOINT_URL
    use_ssl = settings.AWS_S3_USE_SSL
    verify = settings.AWS_S3_VERIFY


class MediaStorage(S3Boto3Storage):
    bucket_name = settings.AWS_MEDIA_BUCKET_NAME
    default_acl = 'public-read'
    custom_domain = settings.AWS_S3_CUSTOM_DOMAIN
    endpoint_url = settings.AWS_S3_ENDPOINT_URL
    use_ssl = settings.AWS_S3_USE_SSL
    verify = settings.AWS_S3_VERIFY
