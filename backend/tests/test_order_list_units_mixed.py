import types
import asyncio
import pytest

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

class _RecipesCol:
    def __init__(self, docs):
        self.docs = docs
    def find(self, q, projection=None):
        return _AsyncCursor(self.docs)

class _InvCol:
    def __init__(self, invs):
        self.invs = invs
    def find(self, q=None, projection=None):
        return _AsyncCursor(self.invs)

class _MenusCol:
    def __init__(self, menu):
        self.menu = menu
    async def find_one(self, q):
        return self.menu

@pytest.mark.asyncio
async def test_order_list_mixed_units(monkeypatch):
    menu = {"date": __import__("datetime").date(2025, 11, 6), "items":[{"recipeId":"r1","quantity":2}]}
    # Recipe uses 500 g Sugar and 1 lb Sugar per unit: total per unit = 500 g + 1 lb
    recipes = [{"_id":"r1","ingredients":[
        {"inventoryId":"i1","quantity":500,"unit":"g","name":"Sugar"},
        {"inventoryId":"i1","quantity":1,"unit":"lb","name":"Sugar"},
    ]}]
    inventory = [{"_id":"i1","name":"Sugar","quantity":0.5,"unit":"kg","reorderLevel":0.0,"targetLevel":0.0}]
    monkeypatch.setattr(ols, "_menus", lambda: _MenusCol(menu), raising=True)
    monkeypatch.setattr(ols, "_recipes", lambda: _RecipesCol(recipes), raising=True)
    monkeypatch.setattr(ols, "_inventory", lambda: _InvCol(inventory), raising=True)

    out = await ols.compute_order_list(menu["date"])
    assert len(out["items"]) == 1
    it = out["items"][0]
    # Per unit: 500 g + 1 lb(0.453592 kg) = 0.5 kg + 0.453592 kg = 0.953592 kg
    # Menu qty 2 -> 1.907184 kg required; onHand 0.5 -> net 1.407184 kg
    assert abs(it["quantity"] - 1.407184) < 1e-3
    assert it["unit"] == "kg"
