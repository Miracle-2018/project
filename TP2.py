import typer
import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import csv

app = typer.Typer()

API_KEY = "1d2f804cb131a9af68b9021d77240a4b"
GET_API_URL = "https://api.itjobs.pt/job/get.json"


#a)

def export_to_csv(filename: str, rows: list[dict]):
    if not rows:
        return

    fieldnames = list(rows[0].keys())

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def determinar_regime(job):
    result = {
        "job_id": job['id'],
        "teamlyzer_rating": None,
        "teamlyzer_description": None,
        "teamlyzer_salary": None,
        "teamlyzer_benefits": []
    }
    
    try:
        namet = job["company"]["name"].lower()
        if namet:
            namet = namet.replace(" ", "-")

          
            url2 = f"https://pt.teamlyzer.com/companies/{namet}"
            response2 = requests.get(url2, headers={"User-Agent": "Bot anti 429"})
            soup2 = BeautifulSoup(response2.text, "lxml")

            
            rat = soup2.find("div", class_="text-center")
            if rat:
                rating = rat.find("span", class_=re.compile(r"text-center\s+[a-z]+_rating"))
                if rating:
                    result["teamlyzer_rating"] = rating.text.strip()[0:3]

           
            description = soup2.find("div", class_="ellipsis center_mobile")
            if description:
                result["teamlyzer_description"] = description.text.strip()

          
            sal = soup2.find('div', class_="row voffset3")
            if sal:
                salary = sal.find('a')
                if salary:
                    result["teamlyzer_salary"] = salary.text.strip()

            
            url3 = f"https://pt.teamlyzer.com/companies/{namet}/benefits-and-values"
            response3 = requests.get(url3, headers={"User-Agent": "Bot anti 429"})
            soup3 = BeautifulSoup(response3.text, "lxml")

            benefits = soup3.find_all("b")
            if benefits:
                result["teamlyzer_benefits"] = [b.text for b in benefits]

    except Exception as e:
        result["error"] = str(e)

    return result
#b)
@app.command("statistics")
def statistics(
    criterio: str = typer.Argument(..., help="Critério de estatísticas (ex: zone)")
):
    
    if criterio != "zone":
        typer.echo("Critério inválido. Use: zone")
        raise typer.Exit(code=1)

    try:
        response = requests.post(
            GET_API_URL.replace("get.json", "list.json"),
            headers={"User-Agent": "Mozilla/5.0"},
            data={"api_key": API_KEY}
        )
        response.raise_for_status()

        data = response.json()
        jobs = data.get("results", [])

        stats = {}

        for job in jobs:
            
            tipo_trabalho = job.get("title", "Desconhecido")

            locations = job.get("locations", [])
            if locations:
                zona = locations[0].get("name", "Desconhecida")
            else:
                zona = "Desconhecida"

            key = (zona, tipo_trabalho)
            stats[key] = stats.get(key, 0) + 1

        rows = []
        for (zona, tipo), total in stats.items():
            rows.append({
                "Zona": zona,
                "Tipo de Trabalho": tipo,
                "Nº de vagas": total
            })

        filename = "estatisticas_vagas_por_zona.csv"
        export_to_csv(filename, rows)

        typer.echo("Ficheiro de exportação criado com sucesso")

    except requests.RequestException as e:
        typer.echo(f"Erro ao obter dados: {e}", err=True)