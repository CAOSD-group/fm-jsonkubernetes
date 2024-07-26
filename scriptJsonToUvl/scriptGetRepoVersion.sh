# Inicializar un nuevo repositorio vacío
git init kubernetes-json-schema
cd kubernetes-json-schema

# Configurar sparse-checkout para obtener solo la carpeta deseada
git remote add origin https://github.com/yannh/kubernetes-json-schema.git
git config core.sparseCheckout true

# Definir la carpeta a clonar
echo "v1.30.2" >> .git/info/sparse-checkout

# Hacer checkout de la rama master
git pull origin master
