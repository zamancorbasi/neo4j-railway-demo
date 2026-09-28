import os
from fastapi import FastAPI
from neo4j import GraphDatabase

app = FastAPI()

# Railway ortam değişkenlerinden adres ve şifreyi alacak
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

@app.get("/")
def read_root():
    return {"message": "Railway Neo4j Demo Çalışıyor!"}

@app.get("/test-db")
def test_database():
    try:
        with driver.session() as session:
            # Neo4j'e basit bir test sorgusu atıp versiyonu alalım
            result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions")
            record = result.single()
            return {
                "status": "Basarili", 
                "neo4j_component": record["name"], 
                "versions": record["versions"]
            }
    except Exception as e:
        return {"status": "Hata", "detail": str(e)}