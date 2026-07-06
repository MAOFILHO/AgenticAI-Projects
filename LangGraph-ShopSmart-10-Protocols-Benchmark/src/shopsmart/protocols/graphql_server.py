"""Local GraphQL 'Product Catalog' service stand-in — run as a subprocess.

`products(query: String)` mirrors mcp_server.search_products, backed by the
same products.json dataset, so GraphQL does real work comparable to the
existing MCP tool.

Run standalone: `python -m shopsmart.protocols.graphql_server`
"""

import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from shopsmart.config import get_data_dir
from shopsmart.data_loader import load_all

_products_db: dict = {}


@strawberry.type
class Product:
    product_id: str
    name: str
    category: str
    price: float
    stock_status: str


@strawberry.type
class Query:
    @strawberry.field
    def products(self, query: str) -> list[Product]:
        query_lower = query.lower()
        return [
            Product(
                product_id=p["product_id"],
                name=p["name"],
                category=p["category"],
                price=p["price"],
                stock_status=p["stock_status"],
            )
            for p in _products_db.values()
            if query_lower in p["name"].lower() or query_lower in p["category"].lower()
        ]


schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)

app = FastAPI(title="ShopSmart GraphQL Product Catalog")
app.include_router(graphql_app, prefix="/graphql")


@app.on_event("startup")
def _load_data():
    global _products_db
    data = load_all(get_data_dir())
    _products_db = data["products_db"]


@app.get("/health")
def health():
    return {"status": "ok", "service": "graphql-product-catalog"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002)
