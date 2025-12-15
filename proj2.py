import typer
import requests
import re
import json
from datetime import datetime
import csv

app = typer.Typer()

API_KEY = "1d2f804cb131a9af68b9021d77240a4b"
LIST_API_URL = "https://api.itjobs.pt/job/list.json"
#a
@app.command("top")
def listar_trabalhos_recentes(n: int = typer.Argument(..., help="Número de trabalhos a listar"),
                              csv_file: str = typer.Option(None, "--csv", help="Nome do ficheiro CSV para exportar")):
    
    
    
    url = f"{LIST_API_URL}?limit={n}&api_key={API_KEY}"
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        trabalhos = response.json().get("results", [])

        if not trabalhos:
            typer.echo("Nenhum trabalho encontrado.")
            return
        
        trabalhos_filtrados = [
            {
                "job_id": t.get("id"),
                'titulo': t.get('title', 'N/A'),
                "job_type": t.get("types", [{}])[0].get("name"),
                "company_id": t.get("company", {}).get("id"),
                'empresa': t.get('company', {}).get('name', 'N/A'),
                'data_publicacao': t.get('publishedAt', 'N/A'),
                'salario': t.get('wage', 'N/A'),
                'localizacao':  t.get("locations", [{}])[0].get("name"),
                
            }

            for t in trabalhos
        ]

        if csv_file:
            exportar_csv(trabalhos, csv_file)
            typer.echo(f"Dados exportados para {csv_file}")
            return

        typer.echo(json.dumps(trabalhos_filtrados, indent=2, ensure_ascii=False))

    except requests.RequestException as erro:
        typer.echo(f"Erro ao aceder à API: {erro}", err=True)

SEARCH_API_URL = "https://api.itjobs.pt/job/search.json"

locality= {"açores": 2, "aveiro": 1, "beja": 3 , "braga": 4, "bragança":5 ,"castelo branco":6,"coimbra":8,"evora": 10,"faro":9 ,"guarda": 11, "internacional": 29,"leiria": 13,"lisboa": 14, "madeira": 15, "portalegre": 12 ,"porto": 18, "santarém":20 ,"setúbal": 17,"viana do castelo": 22, "vila real":21, "viseu":16}
@app.command("search")
def procurar_part_time(
    localidade: str,
    empresa: str,
    n: int,
):
    """Procura trabalhos part-time por localidade e/ou empresa"""
    localidade = localidade.lower()
    query = f"{empresa.lower()} {locality[localidade]}".strip()

    headers = {"User-Agent": "Mozilla/5.0"}
    data = {
        "api_key": API_KEY,
        "q": query,
        "type": 2,  # part-time
        "page": 1  # max per page
    }
    limit = 56

    results = []
    
    page= 1

    try:
        while page <= limit:
            data["page"] = page
            response = requests.post(SEARCH_API_URL, headers=headers, data=data)
            response.raise_for_status()

            pan = response.json().get("results", [])
            if not pan:
                break  # no more pages

            results.extend(pan)
            page += 1


        results = results[:n]
        results_filtrados = [
            {
                "company_name": t.get("company", {}).get("name"),
                "job_id": t.get("id"),
                "job_title": t.get("title"),
                "job_type": t.get("types", [{}])[0].get("name"),
                "job_city": t.get("locations", [{}])[0].get("name"),
            }
            for t in results
        ]

        typer.echo(json.dumps(results_filtrados, indent=2, ensure_ascii=False))

    except requests.RequestException as erro:
        typer.echo(f"Erro ao aceder à API: {erro}", err=True)