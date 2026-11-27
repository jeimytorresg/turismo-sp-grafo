# Grafo de conocimiento: turismo en São Paulo

Práctica bimestral 1 (ciudades inteligentes). Integrantes: Daniel Campoverde, Erick Rodas, Jeimy Torres.

Relaciona alojamientos de Airbnb, espacios culturales de la Secretaría Municipal de Cultura y atracciones de OpenStreetMap, por distrito y por cercanía.

## Estructura
- `datos/`: archivos de origen (Inside Airbnb, SMC, OpenStreetMap) y la capa de distritos.
- `diagramas/`: modelo entidad-relación y esquema semántico RDF (PlantUML y PNG).
- `rdf/esquema_turismo_sp.ttl`: clases y propiedades.
- `rdf/instancias_turismo_sp.ttl`: instancias y relaciones generadas.
- `scripts/transformar_a_rdf.py`: preparación y transformación de los datos a RDF.
- `consultas/consultas_competencia.rq`: consultas SPARQL de las preguntas 1, 2, 4, 6, 8 y 9.
- `evidencias/`: capturas de GraphDB y guía de implementación.

## Cómo generar el Turtle
```
pip install -r requirements.txt
cd scripts
python transformar_a_rdf.py --datos ../datos --salida ../rdf --distritos ../datos/layerdistrito/<archivo>.shp
```
Sin `--distritos` el script no asigna distrito a las atracciones de OpenStreetMap.
