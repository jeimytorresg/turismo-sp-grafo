##### Transformación de datos a RDF (turismo São Paulo, etapa 1C) #####
# uso: python transformar_a_rdf.py --datos ../datos --salida ../rdf --distritos ../datos/layerdistrito.zip
# el esquema (rdf/esquema_turismo_sp.ttl) es el de la etapa 1B; este script solo genera las instancias

import argparse
import io
import json
import re
import unicodedata
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

##### argumentos #####
ap = argparse.ArgumentParser()
ap.add_argument("--datos", required=True)
ap.add_argument("--salida", required=True)
ap.add_argument("--distritos", required=True)  # layerdistrito.zip o .shp
ap.add_argument("--radio_km", type=float, default=1.0)
args = ap.parse_args()

carpeta = Path(args.datos)
salida = Path(args.salida)
salida.mkdir(parents=True, exist_ok=True)

TS = "https://jeimytorresg.github.io/turismo-sp-grafo/turismo-sp#"
ENT = "https://jeimytorresg.github.io/turismo-sp-grafo/recurso/"
res = {}  # resumen para el informe

##### funciones #####
def sin_tildes(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.strip().lower()

def lit(s):
    # texto escapado para Turtle
    s = str(s).replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    return '"' + re.sub(r"\s+", " ", s).strip() + '"'

def dec(v):
    return repr(float(v))

def limpio(v):
    # None si es vacío
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    t = str(v).strip()
    return t if t and t.lower() != "nan" else None

def haversine(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = np.sin((lat2 - lat1) * p / 2) ** 2 + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))

def buscar_archivo(*nombres):
    for n_ in nombres:
        if (carpeta / n_).exists():
            return carpeta / n_
    raise SystemExit("No encontré ninguno de estos archivos en %s: %s" % (carpeta, nombres))

def clave_capa(nombre):
    # la capa de distritos abrevia Cidade y Jardim (CID, JD)
    k = sin_tildes(nombre)
    k = re.sub(r"^cid ", "cidade ", k)
    return re.sub(r"^jd ", "jardim ", k)

def id_dist(k):
    return "ent:distrito_" + re.sub(r"[^a-z0-9]+", "_", k).strip("_")

##### conceptos SKOS del esquema 1B (valor original -> concepto) #####
CONC_HAB = {"Entire home/apt": "ts:TH_CasaDepartamentoCompleto", "Private room": "ts:TH_HabitacionPrivada",
            "Shared room": "ts:TH_HabitacionCompartida", "Hotel room": "ts:TH_HabitacionHotel"}
CONC_ESTADO = {"Em funcionamento": "ts:EF_EnFuncionamiento", "Fechado": "ts:EF_Cerrado",
               "Fechado temporariamente": "ts:EF_CerradoTemporalmente", "Em obras": "ts:EF_EnObras"}
CONC_OSM = {"attraction": "ts:CO_Attraction", "artwork": "ts:CO_Artwork", "museum": "ts:CO_Museum",
            "viewpoint": "ts:CO_Viewpoint", "gallery": "ts:CO_Gallery", "aquarium": "ts:CO_Aquarium",
            "theme_park": "ts:CO_ThemePark", "zoo": "ts:CO_Zoo"}
# tipos de equipamiento: los 3 primeros ya están en el esquema; los demás se agregan aquí (etapa 1C)
CONC_EQUIP = {"Biblioteca": "ts:TE_Biblioteca", "Teatro": "ts:TE_Teatro", "Museu/Acervo": "ts:TE_MuseuAcervo"}
EQUIP_NUEVOS = {"Sala de cinema": ("ts:TE_SalaCine", "Sala de cine"),
                "Casa de Cultura Municipal": ("ts:TE_CasaCulturaMunicipal", "Casa de cultura municipal"),
                "Centro Cultural": ("ts:TE_CentroCultural", "Centro cultural"),
                "Ponto de leitura": ("ts:TE_PuntoLectura", "Punto de lectura"),
                "Bosque de leitura": ("ts:TE_BosqueLectura", "Bosque de lectura"),
                "Escola": ("ts:TE_Escuela", "Escuela"),
                "Auditório": ("ts:TE_Auditorio", "Auditorio"),
                "Estúdio Criativo": ("ts:TE_EstudioCreativo", "Estudio creativo"),
                "Administrativo": ("ts:TE_Administrativo", "Administrativo"),
                "Hemeroteca": ("ts:TE_Hemeroteca", "Hemeroteca"),
                "Gibiteca": ("ts:TE_Gibiteca", "Gibiteca")}
for k_, (iri, _) in EQUIP_NUEVOS.items():
    CONC_EQUIP[k_] = iri

def concepto(tabla, valor, nombre):
    v = str(valor).strip()
    if v not in tabla:
        raise SystemExit("Valor sin concepto en el esquema (%s): %s" % (nombre, v))
    return tabla[v]

##### 1. airbnb #####
aloj = pd.read_csv(buscar_archivo("listings.csv.gz"), compression="gzip", low_memory=False,
                   usecols=["id", "name", "listing_url", "neighbourhood_cleansed", "latitude", "longitude",
                            "room_type", "accommodates", "bedrooms", "price", "review_scores_rating",
                            "review_scores_location", "number_of_reviews"])
res["airbnb_filas_origen"] = len(aloj)
res["airbnb_id_duplicados"] = int(aloj.id.duplicated().sum())
aloj = aloj.drop_duplicates("id")
aloj["precio"] = pd.to_numeric(aloj.price.astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
res["airbnb_sin_precio"] = int(aloj.precio.isna().sum())
res["airbnb_sin_calif_general"] = int(aloj.review_scores_rating.isna().sum())
res["airbnb_sin_calif_ubicacion"] = int(aloj.review_scores_location.isna().sum())
res["airbnb_sin_habitaciones"] = int(aloj.bedrooms.isna().sum())
res["airbnb_sin_distrito"] = int(aloj.neighbourhood_cleansed.isna().sum())
aloj = aloj[aloj.neighbourhood_cleansed.notna()]

##### 2. smc #####
smc = pd.read_excel(buscar_archivo("copia_-espacos-culturais-da-smc.xlsx", "espacos-culturais-da-smc.xlsx"))
smc.columns = [c.replace("\n", " ").strip() for c in smc.columns]
col_nombre = [c for c in smc.columns if c.startswith("nome do equipamento")][0]
res["smc_filas_origen"] = len(smc)
res["smc_nombres_duplicados"] = int(smc[col_nombre].duplicated().sum())

def leer_anio(v):
    t = limpio(v)
    if t is None:
        return None
    if re.fullmatch(r"\d{4}\.0", t):
        t = t[:4]
    return t if re.fullmatch(r"\d{4}", t) else None

smc["anio"] = smc["ano de inauguração"].map(leer_anio)
res["smc_anio_vacio_o_no_valido"] = int(smc.anio.isna().sum())
res["smc_anio_vacio"] = int(smc["ano de inauguração"].isna().sum())
res["smc_anio_no_valido_detalle"] = [str(v) for v, a in zip(smc["ano de inauguração"], smc.anio)
                                     if pd.isna(a) and limpio(v) is not None]

##### 3. osm #####
osm = pd.read_csv(buscar_archivo("atracciones_osm.csv", "saopaulo_atracciones_osm.csv"))
res["osm_filas_origen"] = len(osm)
res["osm_clave_duplicada"] = int(osm.duplicated(["osm_tipo", "osm_id"]).sum())
osm = osm.drop_duplicates(["osm_tipo", "osm_id"]).reset_index(drop=True)
res["osm_sin_nombre"] = int(osm.nombre.isna().sum())

##### 4. distritos #####
# nombre de distrito: con tildes si lo trae la SMC, si no el de Airbnb
nombre_dist = {}
for d in aloj.neighbourhood_cleansed.unique():
    nombre_dist[clave_capa(d)] = d.strip()
for d in smc["distrito"].dropna().unique():
    nombre_dist[clave_capa(d)] = d.strip()

from shapely.geometry import shape, Point
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from shapely import to_wkt
import shapefile
from pyproj import CRS, Transformer

ruta = Path(args.distritos)
prj_texto = None
if ruta.suffix.lower() == ".zip":
    # el zip trae el shapefile dentro de una carpeta
    z = zipfile.ZipFile(ruta)
    base = [n_ for n_ in z.namelist() if n_.lower().endswith(".shp")][0][:-4]
    sf = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), shx=io.BytesIO(z.read(base + ".shx")),
                          dbf=io.BytesIO(z.read(base + ".dbf")))
    if base + ".prj" in z.namelist():
        prj_texto = z.read(base + ".prj").decode("utf-8", "ignore")
else:
    sf = shapefile.Reader(str(ruta))
    if ruta.with_suffix(".prj").exists():
        prj_texto = ruta.with_suffix(".prj").read_text()
campos = [c[0] for c in sf.fields[1:]]
campo_nom = next((c for c in campos if c.lower() in ("nome_dist", "ds_nome", "nm_distrit", "nome", "name")), None)
if campo_nom is None:
    raise SystemExit("No encontré el campo con el nombre del distrito. Campos: %s" % campos)
conv = None
if prj_texto:
    crs = CRS.from_wkt(prj_texto)
    if not crs.is_geographic:
        conv = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform  # a WGS84

poligonos, nombres = [], []
for sr in sf.shapeRecords():
    g = shape(sr.shape.__geo_interface__)
    poligonos.append(transform(conv, g) if conv else g)
    nombres.append(sr.record[campos.index(campo_nom)])

# polígono de cada distrito por clave
poly_dist = {}
for g, nom in zip(poligonos, nombres):
    poly_dist.setdefault(clave_capa(nom), []).append(g)
poly_dist = {k: unary_union(v) if len(v) > 1 else v[0] for k, v in poly_dist.items()}

# distrito de cada atracción OSM (punto en polígono)
arbol = STRtree(poligonos)
osm["distrito_clave"] = None
sin_pareja = set()
for i, r in osm.iterrows():
    pt = Point(r.lon, r.lat)
    for j in arbol.query(pt):
        if poligonos[j].contains(pt):
            k = clave_capa(nombres[j])
            if k in nombre_dist:
                osm.at[i, "distrito_clave"] = k
            else:
                sin_pareja.add(str(nombres[j]))
            break
res["capa_distritos_poligonos"] = len(poligonos)
res["capa_distritos_nombres_sin_pareja"] = sorted(sin_pareja)
res["osm_con_distrito"] = int(osm.distrito_clave.notna().sum())
res["osm_sin_distrito"] = int(osm.distrito_clave.isna().sum())
res["distritos_sin_poligono"] = sorted(k for k in nombre_dist if k not in poly_dist)

##### 5. cercanía alojamiento - atracción #####
lat_a = aloj.latitude.values
lon_a = aloj.longitude.values
ids_a = aloj.id.values
pares = []
for j, r in osm.iterrows():
    dist = haversine(r.lat, r.lon, lat_a, lon_a)
    for i in np.where(dist <= args.radio_km)[0]:
        pares.append((int(ids_a[i]), j))
res["pares_cercania"] = len(pares)

##### 6. escritura del turtle #####
prefijos = (
    "@prefix ts:      <%s> .\n"
    "@prefix ent:     <%s> .\n"
    "@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .\n"
    "@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .\n"
    "@prefix schema:  <https://schema.org/> .\n"
    "@prefix wgs:     <http://www.w3.org/2003/01/geo/wgs84_pos#> .\n"
    "@prefix geo:     <http://www.opengis.net/ont/geosparql#> .\n"
    "@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .\n"
    "@prefix dcterms: <http://purl.org/dc/terms/> .\n\n" % (TS, ENT)
)

def escribir(f, sujeto, tipos, props):
    # props: lista de (predicado, objeto ya formateado)
    lineas = ["%s a %s" % (sujeto, ", ".join(tipos))]
    for p, o in props:
        lineas.append("    %s %s" % (p, o))
    f.write(" ;\n".join(lineas) + " .\n\n")

n_geom = {"punto": 0, "poligono": 0}

def geometria(f, nombre, wkt, tipo):
    # nodo de geometría GeoSPARQL con su WKT
    uri = "ent:geom_" + nombre
    f.write('%s a geo:Geometry ;\n    geo:asWKT "%s"^^geo:wktLiteral .\n\n' % (uri, wkt))
    n_geom[tipo] += 1
    return uri

def punto_wkt(lat, lon):
    return "POINT(%s %s)" % (repr(float(lon)), repr(float(lat)))

n_recursos = {"Distrito": 0, "Alojamiento": 0, "EspacioCultural": 0, "AtraccionTuristica": 0}
subclases = {"Biblioteca": "ts:Biblioteca", "Teatro": "ts:Teatro", "Museu/Acervo": "ts:MuseoAcervo"}
cont_sub = {}
usados_equip = set()

def uri_atr(j):
    return "ent:atraccion_%s_%d" % (osm.at[j, "osm_tipo"], osm.at[j, "osm_id"])

with open(salida / "instancias_turismo_sp.ttl", "w", encoding="utf-8") as f:
    f.write(prefijos)

    # tipos de equipamiento que no están en el esquema 1B (se agregan a partir de los valores reales)
    for valor, (iri, etiqueta) in EQUIP_NUEVOS.items():
        escribir(f, iri, ["skos:Concept"], [("skos:inScheme", "ts:EsquemaTipoEquipamiento"),
                                             ("skos:notation", lit(valor)), ("skos:prefLabel", lit(etiqueta) + "@es")])

    # distritos
    for k in sorted(nombre_dist):
        props = [("schema:name", lit(nombre_dist[k])), ("rdfs:label", lit(nombre_dist[k])),
                 ("ts:claveDistrito", lit(k))]
        if k in poly_dist:
            props.append(("geo:hasGeometry", geometria(f, id_dist(k)[4:], to_wkt(poly_dist[k], rounding_precision=6), "poligono")))
        props.append(("dcterms:source", "ts:fuenteDistritos"))
        escribir(f, id_dist(k), ["ts:Distrito"], props)
        n_recursos["Distrito"] += 1

    # alojamientos
    for r in aloj.itertuples(index=False):
        props = [("ts:idAirbnb", str(int(r.id))), ("ts:ubicadoEnDistrito", id_dist(clave_capa(r.neighbourhood_cleansed)))]
        if limpio(r.name):
            props.append(("schema:name", lit(r.name)))
        props.append(("wgs:lat", dec(r.latitude)))
        props.append(("wgs:long", dec(r.longitude)))
        props.append(("geo:hasGeometry", geometria(f, "alojamiento_%d" % r.id, punto_wkt(r.latitude, r.longitude), "punto")))
        props.append(("ts:tipoHabitacion", concepto(CONC_HAB, r.room_type, "tipo de habitación")))
        props.append(("ts:capacidad", str(int(r.accommodates))))
        if pd.notna(r.bedrooms):
            props.append(("ts:numeroHabitaciones", dec(r.bedrooms)))
        if pd.notna(r.precio):
            props.append(("ts:precioNocheBRL", dec(r.precio)))
        if pd.notna(r.review_scores_rating):
            props.append(("ts:calificacionGeneral", dec(r.review_scores_rating)))
        if pd.notna(r.review_scores_location):
            props.append(("ts:calificacionUbicacion", dec(r.review_scores_location)))
        props.append(("ts:numeroResenas", str(int(r.number_of_reviews))))
        if limpio(r.listing_url):
            props.append(("schema:url", lit(r.listing_url) + "^^xsd:anyURI"))
        props.append(("dcterms:source", "ts:fuenteInsideAirbnb"))
        escribir(f, "ent:alojamiento_%d" % r.id, ["ts:Alojamiento"], props)
        n_recursos["Alojamiento"] += 1

    # espacios culturales
    for n, (_, r) in enumerate(smc.iterrows(), start=1):
        tipo = limpio(r["tipo de equipamento"])
        tipos = ["ts:EspacioCultural"]
        if tipo in subclases:
            tipos.append(subclases[tipo])
            cont_sub[tipo] = cont_sub.get(tipo, 0) + 1
        usados_equip.add(tipo)
        props = [("schema:name", lit(r[col_nombre])),
                 ("ts:tipoEquipamiento", concepto(CONC_EQUIP, tipo, "tipo de equipamiento")),
                 ("ts:estadoFuncionamiento", concepto(CONC_ESTADO, r["status de funcionamento"], "estado")),
                 ("ts:ubicadoEnDistrito", id_dist(clave_capa(r["distrito"])))]
        if limpio(r["subprefeitura"]):
            props.append(("ts:subprefeitura", lit(r["subprefeitura"])))
        if limpio(r["região"]):
            props.append(("ts:region", lit(r["região"])))
        calle = limpio(r["logradouro"])
        if calle:
            num = limpio(r["número do endereço"])
            if num and num.endswith(".0"):
                num = num[:-2]
            props.append(("schema:address", lit(calle + (", " + num if num else ""))))
        v = limpio(r["horário de funcionamento"])
        if v:
            props.append(("schema:openingHours", lit(v)))
        v = limpio(r["site"])
        if v:
            props.append(("schema:url", lit(v) + "^^xsd:anyURI"))
        v = limpio(r["temática"])
        if v:
            props.append(("ts:tematica", lit(v)))
        if r["anio"] is not None:
            props.append(("ts:anioInauguracion", '"%s"^^xsd:gYear' % r["anio"]))
        props.append(("dcterms:source", "ts:fuenteSMC"))
        escribir(f, "ent:espacio_%03d" % n, tipos, props)
        n_recursos["EspacioCultural"] += 1

    # atracciones
    for j, r in osm.iterrows():
        tipos = ["ts:AtraccionTuristica"] + (["ts:Museo"] if r.tourism == "museum" else []) + (["ts:Galeria"] if r.tourism == "gallery" else [])
        props = [("ts:idOsm", str(int(r.osm_id))), ("ts:tipoObjetoOsm", lit(r.osm_tipo)),
                 ("ts:categoriaOsm", concepto(CONC_OSM, r.tourism, "categoría OSM")),
                 ("wgs:lat", dec(r.lat)), ("wgs:long", dec(r.lon)),
                 ("geo:hasGeometry", geometria(f, uri_atr(j)[4:], punto_wkt(r.lat, r.lon), "punto"))]
        if limpio(r.nombre):
            props.append(("schema:name", lit(r.nombre)))
        if limpio(r.calle):
            props.append(("schema:address", lit(r.calle)))
        if limpio(r.horario):
            props.append(("schema:openingHours", lit(r.horario)))
        if limpio(r.sitio_web):
            props.append(("schema:url", lit(r.sitio_web) + "^^xsd:anyURI"))
        if limpio(r.wikidata):
            props.append(("schema:sameAs", "<https://www.wikidata.org/entity/%s>" % limpio(r.wikidata)))
        if r.distrito_clave:
            props.append(("ts:ubicadoEnDistrito", id_dist(r.distrito_clave)))
        props.append(("dcterms:source", "ts:fuenteOpenStreetMap"))
        escribir(f, uri_atr(j), tipos, props)
        n_recursos["AtraccionTuristica"] += 1

    # relación de cercanía (agrupada por alojamiento)
    por_aloj = {}
    for id_a, j in pares:
        por_aloj.setdefault(id_a, []).append(uri_atr(j))
    for id_a, lista in por_aloj.items():
        f.write("ent:alojamiento_%d ts:estaCercaDe %s .\n" % (id_a, ", ".join(lista)))

res["recursos"] = n_recursos
res["geometrias"] = n_geom
res["conceptos_equipamiento_nuevos"] = len(EQUIP_NUEVOS)
res["tipos_equipamiento_en_smc"] = len(usados_equip)
res["subclases_smc"] = cont_sub
res["museos_osm"] = int((osm.tourism == "museum").sum())
res["galerias_osm"] = int((osm.tourism == "gallery").sum())
json.dump(res, open(salida / "resumen_transformacion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(res, ensure_ascii=False, indent=2))
