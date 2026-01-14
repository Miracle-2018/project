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
        all_jobs = []
        page = 1
        
        while True:
            typer.echo(f"Fetching page {page}...")
            
            response = requests.post(
                GET_API_URL.replace("get.json", "list.json"),
                headers={"User-Agent": "Mozilla/5.0"},
                data={
                    "api_key": API_KEY,
                    "page": page
                }
            )
            response.raise_for_status()

            data = response.json()
            jobs = data.get("results", [])
            

            if not jobs:
                break
            
            all_jobs.extend(jobs)
            

            total = data.get("total", 0)
            limit = data.get("limit", 18)  # limit per page

            if len(all_jobs) >= total:
                break
            
            page += 1

        typer.echo(f"Total jobs fetched: {len(all_jobs)}")

        stats = {}

        for job in all_jobs:
            # Get job title
            tipo_trabalho = job.get("title", "Desconhecido")

            # Get location/zone
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

        rows.sort(key=lambda x: (x["Zona"], x["Tipo de Trabalho"]))

        filename = "estatisticas_vagas_por_zona.csv"
        export_to_csv(filename, rows)

        typer.echo(f"Ficheiro de exportação criado com sucesso: {filename}")
        typer.echo(f"Total de combinações zona/tipo: {len(rows)}")

    except requests.RequestException as e:
        typer.echo(f"Erro ao obter dados: {e}", err=True)


@app.command("type")
def tipo_trabalho(
    job_id: int = typer.Argument(..., help="ID do trabalho"),
    csv_out: bool = typer.Option(False, "--csv", help="Exportar informação para CSV")  # <-- NOVO
):
    """Retorna informações Teamlyzer sobre a empresa do job."""
    try:
        response = requests.post(
            GET_API_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            data={"api_key": API_KEY, "id": job_id}
        )
        response.raise_for_status()
        job = response.json()

        if not job or job.get("id") is None:
            typer.echo("not found")
            return

        result = determinar_regime(job)

        if csv_out:
            
            csv_row = {
                "job_id": result.get("job_id"),
                "teamlyzer_rating": result.get("teamlyzer_rating"),
                "teamlyzer_description": result.get("teamlyzer_description"),
                "teamlyzer_salary": result.get("teamlyzer_salary"),
                "teamlyzer_benefits": ", ".join(result.get("teamlyzer_benefits", [])),
            }
            filename = f"job_{job_id}_teamlyzer.csv"
            export_to_csv(filename, [csv_row])
            typer.echo(f"CSV criado com sucesso: {filename}")
        else:
            typer.echo(json.dumps(result, ensure_ascii=False, indent=2))

    except requests.RequestException as erro:
        typer.echo(f"Erro: {erro}", err=True)

#c
roles_en = [
    "Backend",
    "Embedded systems",
    "Fullstack",
    "Administrador de sistemas",
    "Cybersecurity",
    "DevOps ou SRE",
    "Engenheiro de redes",
    "Infraestrutura",
    "Administrador de base de dados",
    "Data scientist, data engineer, machine learning ou big data",
    "Analista funcional",
    "BI, CRM ou ERP",
    "Tester ou QA",
    "Analista de negócio",
    "Gestor de produto",
    "Diretor / tech lead / CTO",
    "Tecnico de suporte",
    "Designer de produto industrial ou equipamentos",
    "Designer grafico ou de comunicacao e multimedia",
    "Engenheiro electronico",
    "Engenheiro electrotecnico",
]


@app.command("list-skills")
def list_skills(
    role: str = typer.Argument(..., help="Role to search for"),
    csv_out: bool = typer.Option(False, "--csv", help="Exportar informação para CSV")  # <-- NOVO
):
    matching_roles = [r for r in roles_en if role.lower() in r.lower()]

    if not matching_roles:
        typer.echo(f"Role '{role}' not found")
        raise typer.Exit(code=1)

    
    all_top_skills = []

    for matched_role in matching_roles:
        role_formatted = (
            matched_role.lower()
            .replace(", ", "-")
            .replace(" ", "-")
        )

        url = (
            "https://pt.teamlyzer.com/companies/jobs"
            f"?profession_role={role_formatted}&order=most_relevant"
        )

        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(response.text, "lxml")

            select = soup.find("select", {"name": "tags"})
            if not select:
                typer.echo("No skills section found.")
                continue

            options = select.find_all("option")[1:]

            skills = []
            for option in options:
                text = option.text.strip()
                match = re.match(r"(.+?)\s*\((\d+)\)", text)
                if match:
                    skills.append({
                        "skill": match.group(1),
                        "count": int(match.group(2))
                    })

            skills.sort(key=lambda x: x["count"], reverse=True)
            top_10 = skills[:10]

            all_top_skills.extend(top_10)

            if not csv_out:
                json_top_10 = [
                    {"skill": s["skill"], "count": s["count"]}
                    for s in top_10
                ]
                typer.echo(json.dumps(json_top_10, indent=2, ensure_ascii=False))

        except Exception as e:
            typer.echo(f"Error processing role '{matched_role}': {e}")

    
    if csv_out and all_top_skills:
        filename = "skills_top10.csv"
        export_to_csv(filename, all_top_skills)
        typer.echo(f"CSV criado com sucesso: {filename}")


if __name__ == "__main__":
    app()
