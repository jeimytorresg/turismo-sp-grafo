##### Transformación de datos a RDF (turismo São Paulo) #####
# uso: python transformar_a_rdf.py --datos ../datos --salida ../rdf [--distritos capa_distritos.shp|.geojson]

import argparse
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

##### argumentos #####
ap = argparse.ArgumentParser()
ap.add_argument("--datos", required=True)
ap.add_argument("--salida", required=True)
ap.add_argument("--distritos", default=None)
ap.add_argument("--radio_km", type=float, default=1.0)
args = ap.parse_args()

carpeta = Path(args.datos)
salida = Path(args.salida)
salida.mkdir(parents=True, exist_ok=True)

TS = "http://example.org/turismo-sp#"
ENT = "http://example.org/turismo-sp/recurso/"
res = {}  # resumen para el informe

##### funciones #####
def sin_tildes(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.strip().lower()

def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", sin_tildes(s)).strip("_")

def lit(s):
    # texto escapado para Turtle
    s = str(s).replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    return '"' + re.sub(r"\s+", " ", s).strip() + '"'

def dec(v):
    return repr(float(v)) if float(v) == float(v) else None

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

##### 1. airbnb #####
aloj = pd.read_csv(carpeta / "listings.csv.gz", compression="gzip", low_memory=False,
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
smc = pd.read_excel(carpeta / "espacos-culturais-da-smc.xlsx")
smc.columns = [c.replace("\n", " ").strip() for c in smc.columns]
col_nombre = [c for c in smc.columns if c.startswith("nome do equipamento")][0]
res["smc_filas_origen"] = len(smc)
res["smc_nombres_duplicados"] = int(smc[col_nombre].duplicated().sum())

def leer_anio(v):
    t = limpio(v)
    if t is None:
        return None
    t = t.split(".")[0] if re.fullmatch(r"\d{4}\.0", t) else t
    return t if re.fullmatch(r"\d{4}", t) else None

smc["anio"] = smc["ano de inauguração"].map(leer_anio)
res["smc_anio_vacio_o_no_valido"] = int(smc.anio.isna().sum())
res["smc_anio_no_valido_detalle"] = [str(v) for v, a in zip(smc["ano de inauguração"], smc.anio)
                                     if pd.isna(a) and limpio(v) is not None]

##### 3. osm #####
osm = pd.read_csv(carpeta / "saopaulo_atracciones_osm.csv")
res["osm_filas_origen"] = len(osm)
res["osm_clave_duplicada"] = int(osm.duplicated(["osm_tipo", "osm_id"]).sum())
osm = osm.drop_duplicates(["osm_tipo", "osm_id"]).reset_index(drop=True)
res["osm_sin_nombre"] = int(osm.nombre.isna().sum())

##### 4. distritos #####
# nombre de distrito: con tildes si lo trae la SMC, si no el de Airbnb
nombre_dist = {}
for d in aloj.neighbourhood_cleansed.unique():
    nombre_dist[sin_tildes(d)] = d.strip()
for d in smc["distrito"].dropna().unique():
    nombre_dist[sin_tildes(d)] = d.strip()

# distrito de cada atracción OSM (punto en polígono) si hay capa
osm["distrito_clave"] = None
if args.distritos:
    from shapely.geometry import shape, Point
    from shapely.strtree import STRtree
    from shapely.ops import transform
    ruta = Path(args.distritos)
    poligonos, nombres = [], []
    if ruta.suffix.lower() == ".geojson":
        gj = json.load(open(ruta, encoding="utf-8"))
        for f in gj["features"]:
            props = f["properties"]
            nom = props.get("neighbourhood") or props.get("nome") or props.get("ds_nome") or list(props.values())[0]
            poligonos.append(shape(f["geometry"]))
            nombres.append(nom)
    else:
        import shapefile
        from pyproj import CRS, Transformer
        sf = shapefile.Reader(str(ruta))
        campos = [c[0] for c in sf.fields[1:]]
        campo_nom = next((c for c in campos if c.lower() in ("nome_dist", "ds_nome", "nm_distrit", "nome", "name")), None)
        if campo_nom is None:
            raise SystemExit("No encontré el campo con el nombre del distrito. Campos: %s" % campos)
        prj = ruta.with_suffix(".prj")
        conv = None
        if prj.exists():
            crs = CRS.from_wkt(prj.read_text())
            if not crs.is_geographic:
                conv = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform
        for sr in sf.shapeRecords():
            g = shape(sr.shape.__geo_interface__)
            poligonos.append(transform(conv, g) if conv else g)
            nombres.append(sr.record[campos.index(campo_nom)])
    arbol = STRtree(poligonos)
    sin_pareja = set()
    for i, r in osm.iterrows():
        pt = Point(r.lon, r.lat)
        for j in arbol.query(pt):
            if poligonos[j].contains(pt):
                k = sin_tildes(nombres[j])
                # la capa abrevia Cidade y Jardim (CID, JD)
                k = re.sub(r"^cid ", "cidade ", k)
                k = re.sub(r"^jd ", "jardim ", k)
                if k in nombre_dist:
                    osm.at[i, "distrito_clave"] = k
                else:
                    sin_pareja.add(str(nombres[j]))
                break
    res["capa_distritos_poligonos"] = len(poligonos)
    res["capa_distritos_nombres_sin_pareja"] = sorted(sin_pareja)
    res["osm_con_distrito"] = int(osm.distrito_clave.notna().sum())
    res["osm_sin_distrito"] = int(osm.distrito_clave.isna().sum())
else:
    res["osm_con_distrito"] = 0
    res["osm_sin_distrito"] = len(osm)

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
    "@prefix ts:   <%s> .\n"
    "@prefix ent:  <%s> .\n"
    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
    "@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .\n\n" % (TS, ENT)
)

def escribir(f, sujeto, tipos, props):
    # props: lista de (predicado, objeto ya formateado)
    lineas = ["%s a %s" % (sujeto, ", ".join(tipos))]
    for p, o in props:
        lineas.append("    %s %s" % (p, o))
    f.write(" ;\n".join(lineas) + " .\n\n")

n_recursos = {"Distrito": 0, "Alojamiento": 0, "EspacioCultural": 0, "AtraccionTuristica": 0}
subclases = {"Biblioteca": "ts:Biblioteca", "Teatro": "ts:Teatro", "Museu/Acervo": "ts:MuseoAcervo"}
cont_sub = {}

with open(salida / "instancias_turismo_sp.ttl", "w", encoding="utf-8") as f:
    f.write(prefijos)

    # distritos
    for k in sorted(nombre_dist):
        escribir(f, "ent:distrito_%s" % k.replace(" ", "_").replace("-", "_"), ["ts:Distrito"],
                 [("ts:nombreDistrito", lit(nombre_dist[k])), ("rdfs:label", lit(nombre_dist[k]))])
        n_recursos["Distrito"] += 1

    def uri_dist(nombre):
        k = sin_tildes(nombre)
        return "ent:distrito_%s" % k.replace(" ", "_").replace("-", "_")

    # alojamientos
    for r in aloj.itertuples(index=False):
        props = [("ts:idAirbnb", str(int(r.id))), ("ts:ubicadoEnDistrito", uri_dist(r.neighbourhood_cleansed))]
        if limpio(r.name):
            props.append(("ts:nombre", lit(r.name)))
        props.append(("ts:latitud", dec(r.latitude)))
        props.append(("ts:longitud", dec(r.longitude)))
        props.append(("ts:tipoHabitacion", lit(r.room_type)))
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
            props.append(("ts:urlAnuncio", '"%s"^^xsd:anyURI' % r.listing_url))
        escribir(f, "ent:alojamiento_%d" % r.id, ["ts:Alojamiento"], props)
        n_recursos["Alojamiento"] += 1

    # espacios culturales
    for n, (_, r) in enumerate(smc.iterrows(), start=1):
        tipo = limpio(r["tipo de equipamento"])
        tipos = ["ts:EspacioCultural"]
        if tipo in subclases:
            tipos.append(subclases[tipo])
            cont_sub[tipo] = cont_sub.get(tipo, 0) + 1
        props = [("ts:nombre", lit(r[col_nombre])), ("ts:tipoEquipamiento", lit(tipo)),
                 ("ts:estadoFuncionamiento", lit(r["status de funcionamento"])),
                 ("ts:ubicadoEnDistrito", uri_dist(r["distrito"])),
                 ("ts:subprefeitura", lit(r["subprefeitura"])), ("ts:region", lit(r["região"]))]
        calle = limpio(r["logradouro"])
        if calle:
            num = limpio(r["número do endereço"])
            if num and num.endswith(".0"):
                num = num[:-2]
            props.append(("ts:direccion", lit(calle + (", " + num if num else ""))))
        for campo, prop in (("horário de funcionamento", "ts:horario"), ("site", "ts:sitioWeb"), ("temática", "ts:tematica")):
            v = limpio(r[campo])
            if v:
                props.append((prop, lit(v)))
        if pd.notna(r["anio"]):
            props.append(("ts:anioInauguracion", '"%s"^^xsd:gYear' % r["anio"]))
        escribir(f, "ent:espacio_%03d" % n, tipos, props)
        n_recursos["EspacioCultural"] += 1

    # atracciones
    def uri_atr(j):
        return "ent:atraccion_%s_%d" % (osm.at[j, "osm_tipo"], osm.at[j, "osm_id"])

    for j, r in osm.iterrows():
        tipos = ["ts:AtraccionTuristica"] + (["ts:Museo"] if r.tourism == "museum" else [])
        props = [("ts:idOsm", str(int(r.osm_id))), ("ts:tipoObjetoOsm", lit(r.osm_tipo)),
                 ("ts:categoriaOsm", lit(r.tourism)), ("ts:latitud", dec(r.lat)), ("ts:longitud", dec(r.lon))]
        if limpio(r.nombre):
            props.append(("ts:nombre", lit(r.nombre)))
        if limpio(r.calle):
            props.append(("ts:direccion", lit(r.calle)))
        if limpio(r.horario):
            props.append(("ts:horario", lit(r.horario)))
        if limpio(r.sitio_web):
            props.append(("ts:sitioWeb", lit(r.sitio_web)))
        if limpio(r.wikidata):
            props.append(("ts:wikidata", lit(r.wikidata)))
        if r.distrito_clave:
            props.append(("ts:ubicadoEnDistrito", uri_dist(r.distrito_clave)))
        escribir(f, uri_atr(j), tipos, props)
        n_recursos["AtraccionTuristica"] += 1

    # relación de cercanía (agrupada por alojamiento)
    por_aloj = {}
    for id_a, j in pares:
        por_aloj.setdefault(id_a, []).append(uri_atr(j))
    for id_a, lista in por_aloj.items():
        f.write("ent:alojamiento_%d ts:estaCercaDe %s .\n" % (id_a, ", ".join(lista)))

res["recursos"] = n_recursos
res["subclases_smc"] = cont_sub
res["museos_osm"] = int((osm.tourism == "museum").sum())
json.dump(res, open(salida / "resumen_transformacion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(res, ensure_ascii=False, indent=2))
