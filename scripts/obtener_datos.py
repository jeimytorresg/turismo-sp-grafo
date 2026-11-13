##### Descarga de las fuentes del proyecto #####
## Uso: python obtener_datos.py
import csv
import json
import urllib.request
import urllib.parse

##### Enlaces #####
url_airbnb = "https://data.insideairbnb.com/brazil/sp/s%C3%A3o-paulo/2026-09-14/data/listings.csv.gz"
url_smc = ("https://dados.prefeitura.sp.gov.br/dataset/ea657891-0118-4cc6-beb6-e3eeb462775c/"
           "resource/27500471-0cec-4e7a-8f63-9ce063fb30c5/download/copia_-espacos-culturais-da-smc.xlsx")
url_overpass = "https://overpass-api.de/api/interpreter"

consulta_osm = """[out:json][timeout:90];
area["name"="São Paulo"]["admin_level"="8"]["boundary"="administrative"]->.a;
(nwr["tourism"~"attraction|museum|gallery|viewpoint|zoo|theme_park|aquarium|artwork"](area.a););
out tags center;"""


##### Descarga directa #####
def descargar(url, destino):
    req = urllib.request.Request(url, headers={"User-Agent": "practica-utpl"})
    with urllib.request.urlopen(req) as r, open(destino, "wb") as f:
        f.write(r.read())
    print("guardado", destino)


##### Consulta a Overpass #####
def descargar_osm(destino):
    datos = urllib.parse.urlencode({"data": consulta_osm}).encode("utf-8")
    req = urllib.request.Request(url_overpass, data=datos, headers={"User-Agent": "practica-utpl"})
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read().decode("utf-8"))

    columnas = ["osm_tipo", "osm_id", "tourism", "nombre", "lat", "lon",
                "calle", "barrio", "sitio_web", "horario", "wikidata"]
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        for e in resp["elements"]:
            t = e.get("tags", {})
            c = e.get("center", e)  # nodos traen lat/lon, vías y relaciones traen center
            w.writerow([e["type"], e["id"], t.get("tourism"), t.get("name"),
                        c.get("lat"), c.get("lon"), t.get("addr:street"),
                        t.get("addr:suburb"), t.get("website"),
                        t.get("opening_hours"), t.get("wikidata")])
    print("guardado", destino, len(resp["elements"]), "registros")


##### Ejecución #####
if __name__ == "__main__":
    descargar(url_airbnb, "../datos/listings.csv.gz")
    descargar(url_smc, "../datos/copia_-espacos-culturais-da-smc.xlsx")
    descargar_osm("../datos/atracciones_osm.csv")
    # La capa de distritos (layerdistrito.zip) se descarga desde la página:
    # https://dados.prefeitura.sp.gov.br/dataset/distritos
