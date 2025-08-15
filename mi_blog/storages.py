# mi_blog/storages.py
from storages.backends.s3boto3 import S3Boto3Storage

class MediaRootS3Boto3Storage(S3Boto3Storage):
    # Guardamos todo bajo "media/" en el bucket
    location = 'media'
    default_acl = None         # objetos privados por defecto (mejor práctica)
    file_overwrite = False     # no pisar si suben mismo nombre
