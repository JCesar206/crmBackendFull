from database import engine, Base
import models

def init_db():
    print("🔄 [Setup] Creando tablas en la base de datos...")
    # Esto crea todas las tablas heredadas de Base
    Base.metadata.create_all(bind=engine)
    print("✅ [Setup] ¡Tablas creadas exitosamente en MySQL!")

if __name__ == "__main__":
    init_db()