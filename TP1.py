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

#b
def exportar_csv_search(results_filtrados, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['company_name', 'job_id', 'job_title', 'job_type', 'job_city'])

        for job in results_filtrados:
            writer.writerow([
                job.get('company_name', 'N/A'),
                job.get('job_id', 'N/A'),
                job.get('job_title', 'N/A'),
                job.get('job_type', 'N/A'),
                job.get('job_city', 'N/A')
            ])

SEARCH_API_URL = "https://api.itjobs.pt/job/search.json"

locality = {
    "açores": 2, "aveiro": 1, "beja": 3, "braga": 4, "bragança": 5,
    "castelo branco": 6, "coimbra": 8, "evora": 10, "faro": 9,
    "guarda": 11, "internacional": 29, "leiria": 13, "lisboa": 14,
    "madeira": 15, "portalegre": 12, "porto": 18, "santarém": 20,
    "setúbal": 17, "viana do castelo": 22, "vila real": 21, "viseu": 16
}

@app.command("search")
def procurar_part_time(
    localidade: str = typer.Argument(..., help="Localidade para pesquisar"),
    empresa: str = typer.Argument(..., help="Nome da empresa para pesquisar"),
    n: int = typer.Argument(..., help="Número de resultados a retornar"),
    csv_file: str = typer.Option(None, "--csv", help="Nome do ficheiro CSV para exportar")
):
    """Procura trabalhos part-time por localidade e empresa"""
    
    localidade_lower = localidade.lower()
    
    if localidade_lower not in locality:
        typer.echo(f"Localidade '{localidade}' não encontrada. Localidades válidas:")
        typer.echo(", ".join(locality.keys()))
        raise typer.Exit(code=1)
    
    location_id = locality[localidade_lower]
    
    headers = {"User-Agent": "Mozilla/5.0"}
    data = {
        "api_key": API_KEY,
        "q": empresa,
        "type": 2,  # part-time
        "page": 1
    }

    results = []
    page = 1
    limit = 100

    try:
        while page <= limit:
            data["page"] = page
            response = requests.post(SEARCH_API_URL, headers=headers, data=data)
            response.raise_for_status()

            json_response = response.json()
            pan = json_response.get("results", [])
            
            if not pan:
                break  # no more pages

      
            for job in pan:
                locations = job.get("locations", [])
             
                if not locations or job.get("allowRemote", False):
                    results.append(job)  # Remote jobs
                elif any(loc.get("id") == str(location_id) for loc in locations):
                    results.append(job)  # Matching location
            
            page += 1
            
            if len(results) >= n:
                break

        # Limit to n results
        results = results[:n]
        
        typer.echo(f"\nTotal results found: {len(results)}")
        
        results_filtrados = [
            {
                "company_name": t.get("company", {}).get("name"),
                "job_id": t.get("id"),
                "job_title": t.get("title"),
                "job_type": t.get("types", [{}])[0].get("name") if t.get("types") else None,
                "job_city": t.get("locations", [{}])[0].get("name") if t.get("locations") else "Remoto",
            }
            for t in results
        ]
        
        if csv_file:
            exportar_csv_search(results_filtrados, csv_file)
            typer.echo(f"Dados exportados para {csv_file}")
        else:
            typer.echo(json.dumps(results_filtrados, indent=2, ensure_ascii=False))

    except requests.RequestException as erro:
        typer.echo(f"Erro ao aceder à API: {erro}", err=True)
        
#c)

GET_API_URL = "https://api.itjobs.pt/job/get.json"

def determinar_regime(job):
    if job.get("allowRemote"):
        return "Remoto"
    
    texto = job.get("body", "") + " " + job.get("title", "")
    
    if re.search(r"[Hh][ií]brido|[Hh]ybrid", texto):
        return "Híbrido"
    elif re.search(r"[Rr]emoto|[Rr]emote|[Tt]eletrabalho", texto):
        return "Remoto"
    elif re.search(r"[Pp]resencial|[Oo]n-?site|[Ee]scritório|[Oo]ffice", texto):
        return "Presencial"
    
    return "Não especificado"

@app.command("type")
def tipo_trabalho(job_id: int = typer.Argument(..., help="ID do trabalho")):
    """Retorna o tipo de regime de trabalho de um job"""
    try:
        response = requests.post(GET_API_URL, 
                                headers={"User-Agent": "Mozilla/5.0"}, 
                                data={"api_key": API_KEY, "id": job_id})
        response.raise_for_status()
        job = response.json()
        
        if not job or job.get("id") is None:
            typer.echo("not found")
            return
        
        typer.echo(determinar_regime(job).lower())
    except requests.RequestException as erro:
        typer.echo(f"Erro: {erro}", err=True)
        
#d)
@app.command("skills")
def contar_skills(
    data_inicio: str = typer.Argument(..., help="Data início (formato: YYYY-MM-DD)"),
    data_fim: str = typer.Argument(..., help="Data fim (formato: YYYY-MM-DD)"),
):
    
    skills = [
        "Python", "Java", "JavaScript", "TypeScript", "C#", "C\\+\\+", "PHP", "Ruby", "Go", "Rust",
        "React", "Angular", "Vue", "Node.js", "Django", "Flask", "Spring", "Laravel",
        "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Oracle",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Jenkins", "GitLab", "GitHub",
        "Machine Learning", "AI", "Data Science", "Deep Learning", "TensorFlow", "PyTorch",
        "Agile", "Scrum", "DevOps", "CI/CD", "Microservices", "REST", "GraphQL",
        "Linux", "Git", "Terraform", "Ansible"
    ]
    
    try:
        response = requests.get(f"{LIST_API_URL}?api_key={API_KEY}&limit=100", 
                               headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        trabalhos = response.json().get("results", [])
        #print(trabalhos.get("body", ""))
        
        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d")
        
        trabalhos_filtrados = [
            t for t in trabalhos 
            if t.get("publishedAt") and 
            dt_inicio <= datetime.strptime(t["publishedAt"].split(" ")[0], "%Y-%m-%d") <= dt_fim
        ]     
        
        if not trabalhos_filtrados:
            typer.echo("[]")
            return
        
        skill_count = {skill.replace("\\+\\+", "++"): 0 for skill in skills}
        
        for t in trabalhos_filtrados:
            texto = t.get("body", "") + " " + t.get("title", "")
            for skill in skills:
                matches = re.findall(rf'\b{skill}\b', texto, re.IGNORECASE)
                if matches:
                    skill_count[skill.replace("\\+\\+", "++")] += len(matches)
        
        skills_ordenadas = {k: v for k, v in sorted(skill_count.items(), key=lambda x: x[1], reverse=True) if v > 0}
        
        typer.echo(json.dumps([skills_ordenadas], ensure_ascii=False))
        
    except ValueError as e:
        typer.echo(f"Erro no formato da data. Use YYYY-MM-DD: {e}", err=True)
    except requests.RequestException as erro:
        typer.echo(f"Erro ao aceder à API: {erro}", err=True)
        
#e)
def exportar_csv(trabalhos, filename):

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['titulo', 'empresa', 'descricao', 'data_publicacao', 'salario', 'localizacao'])

        for trabalho in trabalhos:
            descricao_raw = trabalho.get('body', 'N/A')
            descricao_limpa = re.sub(r'<[^>]+>', '', descricao_raw) 
            descricao_limpa = descricao_limpa.strip()
            writer.writerow([
                trabalho.get('title', 'N/A'),
                trabalho.get('company', {}).get('name', 'N/A'),
                descricao_limpa[:200] + '...',
                trabalho.get('publishedAt', 'N/A'),
                trabalho.get('wage', 'N/A'),
                trabalho.get('locations', [{}])[0].get('name', 'N/A')
            ])

if __name__ == "__main__":
    app()