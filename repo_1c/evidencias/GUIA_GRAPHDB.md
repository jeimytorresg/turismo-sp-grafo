# Guía para implementar y explorar el grafo en GraphDB

Los pasos están pensados para GraphDB Free (Workbench en http://localhost:7200). Los nombres de menús pueden variar un poco según la versión.

## 1. Crear el repositorio
1. En el Workbench: **Setup > Repositories > Create new repository > GraphDB Repository**.
2. Repository ID: `turismo-sp`. Ruleset: dejar el que viene por defecto (RDFS-Plus optimized). Crear.
3. Arriba a la derecha, seleccionar `turismo-sp` como repositorio activo.

**Evidencia 1:** captura de la lista de repositorios con `turismo-sp` creado y seleccionado.

## 2. Importar los archivos Turtle
Importar los dos archivos, en este orden:
1. `rdf/esquema_turismo_sp.ttl` (clases y propiedades).
2. `rdf/instancias_turismo_sp.ttl` (instancias y relaciones, unos 40 MB).

Pasos: **Import > User data > Upload RDF files**, elegir el archivo, **Import**. En la ventana de opciones dejar el grafo por defecto ("The default graph") y el formato Turtle. Esperar a que el estado diga que terminó.

Si el navegador se queda sin responder con el archivo grande, copiar el `.ttl` a la carpeta `graphdb-import` de GraphDB y usar **Import > Server files**.

**Evidencia 2:** captura de la pantalla Import con los dos archivos y su estado de importación terminado.

## 3. Comprobar la importación
En **SPARQL**, ejecutar:

```sparql
SELECT (COUNT(*) AS ?tripletas) WHERE { ?s ?p ?o }
```

Con el ruleset por defecto, GraphDB agrega tripletas inferidas, así que este número será mayor que el del archivo. Para comparar con el `.ttl` se puede ver en **Repositories** el número de "Explicit triples", que debe ser igual a la suma de las tripletas del esquema y las instancias (ver `rdf/resumen_transformacion.json` y el informe).

Conteo de instancias por clase:

```sparql
PREFIX ts: <http://example.org/turismo-sp#>
SELECT ?clase (COUNT(?s) AS ?instancias)
WHERE { ?s a ?clase . FILTER(STRSTARTS(STR(?clase), STR(ts:))) }
GROUP BY ?clase
ORDER BY DESC(?instancias)
```

**Evidencia 3:** capturas del número de tripletas explícitas y del resultado del conteo por clase.

## 4. Explorar recursos, propiedades y relaciones
Usar **Explore > Graphs overview** y **Explore > Class hierarchy**, y luego **Explore > Visual graph**.

Recursos sugeridos para las capturas (el nombre se escribe en el cuadro de búsqueda o se pega el URI):
- Un distrito: `http://example.org/turismo-sp/recurso/distrito_republica`
- Un museo de OpenStreetMap: buscar "Museu de Arte de São Paulo" con la búsqueda de recursos.
- Un espacio cultural: `http://example.org/turismo-sp/recurso/espacio_001`
- Un alojamiento: `http://example.org/turismo-sp/recurso/alojamiento_` seguido de un id que exista (se puede tomar de la consulta de la pregunta 1 ampliada con `LIMIT 5`).

**Evidencias 4 a 7:**
- 4: **Class hierarchy**, mostrando `Lugar > PuntoDeInteres > EspacioCultural / AtraccionTuristica` y las subclases.
- 5: página de un recurso (clic en el URI en el resultado de una consulta, o **Explore > Resource**), con su tipo y sus propiedades descriptivas.
- 6: **Visual graph** de un distrito con sus espacios culturales y alojamientos (usar pocos nodos para que se lea).
- 7: **Visual graph** de un alojamiento con `ts:estaCercaDe` hacia atracciones.

## 5. Consultas de competencia
Ejecutar cada consulta de `consultas/consultas_competencia.rq` en **SPARQL** y tomar captura del resultado (preguntas 1, 2, 4, 6, 8 y 9).

**Evidencias 8 a 13:** una captura por consulta, con la consulta visible y los resultados.

## Dónde guardar las capturas
Guardarlas en `evidencias/` con nombres como `01_repositorio.png`, `02_importacion.png`, `03_tripletas.png`, etc.
