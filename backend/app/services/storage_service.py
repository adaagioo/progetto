from __future__ import annotations
from pathlib import Path
from typing import BinaryIO
from app.core.config import settings


class StorageDriver:
	async def save(self, key: str, stream: BinaryIO) -> str: ...

	async def read(self, key: str) -> bytes: ...

	async def delete(self, key: str) -> None: ...


class LocalStorage(StorageDriver):
	def __init__(self, base: str) -> None:
		self.base = Path(base)
		self.base.mkdir(parents=True, exist_ok=True)

	async def save(self, key: str, stream: BinaryIO) -> str:
		p = self.base / key
		p.parent.mkdir(parents=True, exist_ok=True)
		with open(p, "wb") as f: f.write(stream.read())
		return str(p)

	async def read(self, key: str) -> bytes:
		return (self.base / key).read_bytes()

	async def delete(self, key: str) -> None:
		p = self.base / key
		if p.exists(): p.unlink()


try:
	import aiohttp
	import aioboto3
except Exception:
	aioboto3 = None


class S3Storage(StorageDriver):
	def __init__(self, bucket: str, endpoint: str | None, access: str | None, secret: str | None, region: str | None):
		self.bucket = bucket
		self.endpoint = endpoint
		self.access = access
		self.secret = secret
		self.region = region

	async def save(self, key: str, stream: BinaryIO) -> str:
		if aioboto3 is None:
			raise RuntimeError("aioboto3 not installed")
		session = aioboto3.Session()
		async with session.client("s3", endpoint_url=self.endpoint, aws_access_key_id=self.access,
		                          aws_secret_access_key=self.secret, region_name=self.region) as s3:
			await s3.put_object(Bucket=self.bucket, Key=key, Body=stream.read())
		return f"s3://{self.bucket}/{key}"

	async def read(self, key: str) -> bytes:
		if aioboto3 is None:
			raise RuntimeError("aioboto3 not installed")
		session = aioboto3.Session()
		async with session.client("s3", endpoint_url=self.endpoint, aws_access_key_id=self.access,
		                          aws_secret_access_key=self.secret, region_name=self.region) as s3:
			obj = await s3.get_object(Bucket=self.bucket, Key=key)
			return await obj["Body"].read()

	async def delete(self, key: str) -> None:
		if aioboto3 is None:
			raise RuntimeError("aioboto3 not installed")
		session = aioboto3.Session()
		async with session.client("s3", endpoint_url=self.endpoint, aws_access_key_id=self.access,
		                          aws_secret_access_key=self.secret, region_name=self.region) as s3:
			await s3.delete_object(Bucket=self.bucket, Key=key)


def get_storage() -> StorageDriver:
	if settings.STORAGE_DRIVER == "s3":
		return S3Storage(
			bucket=settings.S3_BUCKET or "ristobrain",
			endpoint=str(settings.S3_ENDPOINT_URL) if settings.S3_ENDPOINT_URL else None,
			access=settings.S3_ACCESS_KEY,
			secret=settings.S3_SECRET_KEY,
			region=settings.S3_REGION,
		)
	return LocalStorage(settings.STORAGE_LOCAL_PATH)
