# backend/app/api/V1/suppliers.py
from __future__ import annotations
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.repositories.files_repo import get_meta, insert_meta
from backend.app.repositories.suppliers_deps_repo import summarize_supplier_dependencies
from backend.app.schemas.files import FileRef
from backend.app.schemas.suppliers import Supplier, SupplierCreate, SupplierUpdate, SupplierDependencies
from backend.app.repositories import suppliers_repo as repo
from backend.app.services.storage_service import get_storage

router = APIRouter()
RESOURCE = "suppliers"


@router.post("/suppliers", response_model=Supplier)
async def create_supplier(payload: SupplierCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	sid = await repo.create(payload.model_dump(exclude_unset=True))
	doc = await repo.get_by_id(sid)
	return Supplier(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})


@router.get("/suppliers", response_model=List[Supplier])
async def list_suppliers(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", True):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await repo.list_all()
	return [Supplier(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"}) for d in docs]


@router.get("/suppliers/{supplier_id}", response_model=Supplier)
async def get_supplier(supplier_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", True):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = await repo.get_by_id(supplier_id)
	if not doc:
		raise HTTPException(status_code=404, detail="Not found")
	return Supplier(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})


@router.put("/suppliers/{supplier_id}", response_model=Supplier)
async def update_supplier(supplier_id: str, payload: SupplierUpdate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await repo.update(supplier_id, payload.model_dump(exclude_unset=True))
	if not ok:
		raise HTTPException(status_code=404, detail="Not found")
	doc = await repo.get_by_id(supplier_id)
	return Supplier(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k != "_id"})


@router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await repo.delete(supplier_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Not found")
	return {"ok": True}


@router.get("/suppliers/{supplier_id}/dependencies", response_model=SupplierDependencies)
async def supplier_dependencies(supplier_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", True):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	inv_defaults, recv_refs = await summarize_supplier_dependencies(supplier_id)
	has_refs = (inv_defaults > 0 or recv_refs > 0)
	return SupplierDependencies(
		supplierId=supplier_id,
		hasReferences=has_refs,
		references={
			"inventoryDefaults": inv_defaults,
			"receiving": recv_refs,
		},
	)


@router.post("/suppliers/{supplier_id}/files", response_model=FileRef, status_code=201)
async def suppliers_attach_file(
		supplier_id: str,
		file: UploadFile = File(...),
		user: dict = Depends(get_current_user)
):
	"""Upload and attach a file to a supplier"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Upload file to storage
	data = await file.read()
	storage = get_storage()
	path, size = storage.save_file(file.filename, file.content_type, data)

	# Create file metadata
	meta_id = await insert_meta({
		"filename": file.filename,
		"contentType": file.content_type,
		"size": size,
		"path": path,
		"ownerId": str(user.get("_id")) if user.get("_id") else None,
	})

	# Get the created metadata
	meta = await get_meta(meta_id)
	if not meta:
		raise HTTPException(status_code=500, detail="Failed to create file metadata")

	# Get public URL for the file
	url = storage.get_public_url(meta["path"])

	file_ref = {
		"fileId": str(meta["_id"]),
		"filename": meta["filename"],
		"contentType": meta.get("contentType"),
		"size": meta.get("size", 0),
		"path": meta["path"],
		"url": url,
	}

	ok = await repo.attach_file(supplier_id, file_ref)
	if not ok:
		raise HTTPException(status_code=404, detail="Supplier not found")

	return FileRef(**file_ref)


@router.delete("/suppliers/{supplier_id}/files/{file_id}")
async def suppliers_detach_file(
		supplier_id: str,
		file_id: str,
		user: dict = Depends(get_current_user)
):
	print(f"[SUPPLIER DELETE FILE] supplier_id={supplier_id}, file_id={file_id}, user={user.get('email')}")

	# Validate file_id
	if not file_id or file_id == "undefined":
		raise HTTPException(status_code=400, detail="Invalid file_id. Frontend is not sending the correct file ID.")

	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	ok = await repo.detach_file(supplier_id, file_id)
	if not ok:
		raise HTTPException(status_code=404, detail="Supplier or file not found")
	return {"ok": True}
