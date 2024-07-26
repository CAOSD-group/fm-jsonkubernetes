import os

def count_files_in_directory(directory_path):
    try:
        # Lista todos los archivos y directorios en el directorio dado
        entries = os.listdir(directory_path)
        # Filtra solo los archivos
        files = [entry for entry in entries if os.path.isfile(os.path.join(directory_path, entry))]
        file_count = len(files)
        return file_count
    except Exception as e:
        print(f"Error al contar los archivos en {directory_path}: {e}")
        return 0

# Ejemplo de uso
directory_path = r'C:\projects\investigacion\kubernetes-json-v1.30.2\v1.30.2'
file_count = count_files_in_directory(directory_path)
print(f"El número de archivos en la carpeta '{directory_path}' es: {file_count}")

### Version kubernetes-json-v1.30.2\v1.30.2' contiene 1178 archivos

"""
#Version mas simple
import os

count = 0
dir_path = r'E:\account'
for path in os.scandir(dir_path):
    if path.is_file():
        count += 1
print('file count:', count)
"""

