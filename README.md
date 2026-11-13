# Grafo de conocimiento sobre turismo en São Paulo

Práctica bimestral 1A + 1B (Universidad Técnica Particular de Loja).
Integrantes: Daniel Campoverde, Erick Rodas, Jeimy Torres.

El proyecto relaciona los alojamientos de corta estancia (Inside Airbnb) con los espacios culturales de la
Secretaría Municipal de Cultura (SMC) y con las atracciones turísticas de OpenStreetMap, por distrito y por cercanía.

## Estructura

| Carpeta | Contenido |
|---|---|
| `datos/` | `listings.csv.gz` (Inside Airbnb), `copia_-espacos-culturais-da-smc.xlsx` (SMC), `atracciones_osm.csv` (OpenStreetMap) y `layerdistrito.zip` (capa de distritos) |
| `modelos/` | Modelo entidad-relación (`.puml` y `.png`), esquema semántico RDF (`.dot` y `.png`), y diagrama de reutilización de vocabularios |
| `rdf/` | `esquema_turismo_sp.ttl`, esquema semántico en Turtle |
| `scripts/` | `obtener_datos.py`, descarga de las fuentes |

## Vocabularios reutilizados

Schema.org, GeoSPARQL, WGS84, DBpedia Ontology, SKOS, Dublin Core Terms, DCAT y FOAF.
El espacio de nombres propio es `https://ericroco.github.io/turismo-sp-grafo/turismo-sp#` (prefijo `ts:`).

## Fuentes

- Inside Airbnb: https://insideairbnb.com/get-the-data/
- SMC, Portal de Dados Abertos: https://dados.prefeitura.sp.gov.br/dataset/cadastro-dos-equipamentos-municipais-de-cultura2
- OpenStreetMap (Overpass API): https://overpass-api.de/api/interpreter (datos con licencia de https://www.openstreetmap.org/copyright)
- Distritos, Portal de Dados Abertos: https://dados.prefeitura.sp.gov.br/dataset/distritos
