import types
import asyncio
import pytest

# Target modules
import backend.app.services.prep_list_service as pls
import backend.app.services.order_list_service as ols


class _AsyncCursor:
	def __init__(self, docs):
		self._docs = docs
		self._i = 0

	def sort(self, *args, **kwargs):
		return self

	def limit(self, *args, **kwargs):
		return self

	def __aiter__(self):
		self._i = 0
		return self

	async def __anext__(self):
		if self._i >= len(self._docs):
			raise StopAsyncIteration
		d = self._docs[self._i]
		self._i += 1
		return d


class _Col:
	def __init__(self, docs_map):
		self.docs_map = docs_map

	async def find_one(self, query):
		if "date" in query:
			for d in self.docs_map.get("menus", []):
				if d["date"] == query["date"]:
					return d
		if "_id" in query:
			for coll in self.docs_map.values():
				for d in coll:
					if d.get("_id") == query["_id"]:
						return d
		return None

	def find(self, query, projection=None):
		# Simplified: recipes query by _id $in
		if "_id" in query and isinstance(query["_id"], dict) and "$in" in query["_id"]:
			ids = set(str(x) for x in query["_id"]["$in"])
			out = [d for d in self.docs_map.get("recipes", []) if str(d["_id"]) in ids]
			return _AsyncCursor(out)
		return _AsyncCursor([])


@pytest.mark.asyncio
async def test_prep_list_aggregates_by_preparation(monkeypatch):
	# menu with one recipe * 2
	menu = {"date": __import__("datetime").date(2025, 11, 6), "items": [{"recipeId": "r1", "quantity": 2}]}
	recipes = [{
		"_id": "r1",
		"ingredients": [
			{"preparationId": "p1", "quantity": 1, "unit": "pcs", "name": "Dough ball"},
			{"preparationId": "p1", "quantity": 0.5, "unit": "pcs", "name": "Dough ball"},
		]
	}]
	preps = [{"_id": "p1", "name": "Dough"}]
	docs = {"menus": [menu], "recipes": recipes, "preparations": preps}

	# Monkeypatch helpers to use in-memory data
	monkeypatch.setattr(pls, "_menus", lambda: _Col(docs), raising=True)
	monkeypatch.setattr(pls, "_recipes", lambda: _Col(docs), raising=True)

	class _PCol:
		def find(self, q, projection=None):
			return _AsyncCursor(preps)

	monkeypatch.setattr(pls, "_preps", lambda: _PCol(), raising=True)

	out = await pls.compute_prep_list(menu["date"])
	assert out["date"] == menu["date"]
	assert len(out["tasks"]) == 1
	t = out["tasks"][0]
	# total quantity = (1 + 0.5) * 2 = 3
	assert t["name"] == "Dough"
	assert abs(t["quantity"] - 3.0) < 1e-6


@pytest.mark.asyncio
async def test_order_list_reorder_policy(monkeypatch):
	menu = {"date": __import__("datetime").date(2025, 11, 6), "items": []}
	inventory = [
		{"_id": "i1", "name": "Flour", "quantity": 2.0, "unit": "kg", "reorderLevel": 5.0, "targetLevel": 10.0}]
	recipes = []
	docs = {"menus": [menu], "recipes": recipes, "inventory": inventory}

	# Monkeypatch collections
	monkeypatch.setattr(ols, "_menus", lambda: _Col(docs), raising=True)

	# recipes empty
	class _InvCol:
		def find(self, *a, **k):
			return _AsyncCursor(inventory)

	monkeypatch.setattr(ols, "_recipes", lambda: _Col(docs), raising=True)
	monkeypatch.setattr(ols, "_inventory", lambda: _InvCol(), raising=True)

	out = await ols.compute_order_list(menu["date"])
	assert len(out["items"]) == 1
	# No menu need, but below reorder level -> order up to target (10 - 2) = 8 kg
	it = out["items"][0]
	assert it["name"] == "Flour"
	assert abs(it["quantity"] - 8.0) < 1e-6
	assert it["unit"] == "kg"


@pytest.mark.asyncio
async def test_order_list_unit_conversion_and_need(monkeypatch):
	menu = {"date": __import__("datetime").date(2025, 11, 6), "items": [{"recipeId": "r1", "quantity": 4}]}
	# Recipe needs 500 g per unit -> 2000 g total = 2 kg
	recipes = [{"_id": "r1", "ingredients": [{"inventoryId": "i1", "quantity": 500, "unit": "g", "name": "Sugar"}]}]
	inventory = [{"_id": "i1", "name": "Sugar", "quantity": 1.0, "unit": "kg", "reorderLevel": 0.0, "targetLevel": 3.0}]
	docs = {"menus": [menu], "recipes": recipes, "inventory": inventory}

	# Monkeypatch
	monkeypatch.setattr(ols, "_menus", lambda: _Col(docs), raising=True)

	class _RCol:
		def find(self, q, projection=None):
			return _AsyncCursor(recipes)

	class _InvCol:
		def find(self, q, projection=None):
			return _AsyncCursor(inventory)

	monkeypatch.setattr(ols, "_recipes", lambda: _RCol(), raising=True)
	monkeypatch.setattr(ols, "_inventory", lambda: _InvCol(), raising=True)

	out = await ols.compute_order_list(menu["date"])
	assert len(out["items"]) == 1
	it = out["items"][0]
	# required 2 kg, onHand 1 kg -> net 1; targetLevel 3 -> reorder wants +2; choose max = 2 kg
	assert it["name"] == "Sugar"
	assert abs(it["quantity"] - 2.0) < 1e-6
