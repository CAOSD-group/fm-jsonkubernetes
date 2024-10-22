# fm-json-kubernetes

El proyecto tiene como objetivo convertir cualquier versión de los esquemas de Kubernetes en un feature model UVL. 

En la carpeta scriptJsonToUvl se encuentran los siguientes archivos:

- ~~analisisScript.py: es un archivo en desarrollo que busca poder mapear las descripciones filtradas de los features a restricciones o constraints válidas en el modelo.~~ (Deprecated)
- analisisScriptNpl.py: es una versión del primer script en la que se añade NPL o Tratamiento del Lenguaje Natural para tratar de mejorar la obtención de las restricciones de las descripciones. (En desarrollo)
- conver0SinDatos.py: es una versión del archivo base de conversión que omite el Tipo de datos de los features (String, Boolean, Integer) para poder analizarlo con flamapy.
- ~~convert0.py: archivo base de la conversión que mantiene una funcionalidad testeada y robusta. Esta se actualiza cuando los cambios estan probados y validados en convert01Large.py.~~
- ~~convert01Large.py: esta es la versión principal de desarrollo que se esta usando para desarrollar el script. Esta versión es la mas avanzada y donde se suelen subir las actualizaciones y cambios, difiere de las demás en que aquí se extienden las referencias, se están añadiendo funciones para manejar constraints y más...~~
- ~~convert02Short.py: esta es una versión paralela a la anterior que no extiende tanto las referencias y trata de evitar la repetición de referencias que ya han sido procesadas.~~
- descripcionesManuales.txt: es este fichero de texto se están añadiendo manualmente las descripcciones que tienen restricciones, valores o dependencias para tener nota de las posibles conversiones a realizar en un futuro.
- descriptions_01.json: archivo en formato json con las descripciones filtradas del script base, de aquí se extraen las descripciones en los analisis*. están divididas por grupos con el nombre del feature y el tipo de dato que se describe.
- getNumberFiles.py: fichero de prueba para comprobar cuantos archivos tiene cada carpeta obtenida de la versión de kubernetes-json-schema.
- kubernetes_combined_01_constraints.uvl: resultado de la conversión de los esquemas json de kubernetes. Este es el feature model actual que sigue en proceso de añadir las constraints restantes (7651 sin contar las restricciones).
- kubernetes_combined_01_original.uvl: feature model original con la primera versión obtenida (5712 lineas)
- kubernetes_combined_01.uvl: feature model actual y más avanzado, 76.075 líneas. (En desarrollo)
- restrictions02.txt: archivo de prueba donde se obtienen restricciones "automaticamente" (En desarrollo)
- scriptGetRepoVersion.sh: script para obtener una versión específica de [kubernetes-json-schema](https://github.com/yannh/kubernetes-json-schema/tree/master) 

En la carpeta v.30.2 se encuentran los siguientes archivos:

- _definitions.json_: es el archivo principal de los esquemas de Kubernetes donde se concentran todos los esquemas repartidos en los miles de archivos individuales de cada versión de Kubernetes. Se usa este archivo como base para construir el modelo uvl y corresponde a la versión V.30.2.


# Funcionamiento del programa: 

En la siguiente imagen se puede observar de manera visual como se relacionan los archivos.

![prueba01 drawio](https://github.com/user-attachments/assets/81de09c1-f7b0-46f7-a2b5-829410c31d12)


# ¿Cómo usar el programa?

De momento el uso del programa es sencillo, consta de 2 pasos y son los siguientes:

1. Obtener una versión de kubernetes-json. Esto se puede realizar mediante el fichero [scriptGetRepoVersion.sh](https://github.com/CAOSD-group/fm-json-kubernetes/blob/main/scriptJsonToUvl/scriptGetRepoVersion.sh) o descargarse el archivo _definitions.json de la versión que se desee convertir. Si se realiza con la primera opción lo único que habría que modificar es la línea "echo "v1.30.2" >> .git/info/sparse-checkout" con el nombre de la carpeta que contiene la versión deseada. Este script crea un repositorio local con el contenido de la carpeta especificada. Se puede ejecutar directamente con Git Bash y el comando "./scriptGetRepoVersion.sh" o línea por línea desde el cmd o PowerShell. También se puede probar con la versión usada para el desarrollo de este proyecto en la carpeta [v.30.2](https://github.com/CAOSD-group/fm-json-kubernetes/tree/main/v.30.2).

2. Ejecutar el script [convert01Large](https://github.com/CAOSD-group/fm-json-kubernetes/blob/main/scriptJsonToUvl/convert01Large.py). Este es el script en desarrollo más avanzado y completo por el momento. La ejecución es simple usando Python con el comando "python .\convert01Large.py", el único detalle es comprobar la ruta relativa asociada al archivo _definitions.json que se menciona al final del fichero "definitions_file = '../kubernetes-json-v1.30.2/v1.30.2/_definitions.json'", asignando la ruta apropiada en cada caso.

Tras realizar estos pasos se obtiene el archivo con el modelo kubernetes_combined_01.uvl.


El proyecto sigue en desarrollo y con mucho margen de mejora...