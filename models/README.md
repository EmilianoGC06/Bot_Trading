# Modelo

Aquí va `modelo_mlp.json`: el MLP elegido en la práctica (avance 2, MLP16/32/64), exportado desde Colab.

1. En Colab, al final del notebook del avance 2 (misma sesión), ejecuta `scripts/exportar_modelo_colab.py`.
2. Descarga `modelo_mlp.json` y cópialo a esta carpeta.
3. Haz commit del archivo: el modelo y su escalador quedan versionados junto con el código.

El JSON contiene los pesos de cada capa, la media y escala del escalador (ajustado solo con TR), la media y desviación del objetivo, y metadatos (configuración, RMSE de VA, fecha). Si el archivo no existe, el bot usa el pronóstico cero y la interfaz lo indica.
