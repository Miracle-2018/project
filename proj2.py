import typer
import requests
import re
import json
from datetime import datetime
import csv

app = typer.Typer()

API_KEY = "1d2f804cb131a9af68b9021d77240a4b"
LIST_API_URL = "https://api.itjobs.pt/job/list.json"

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
        
        if csv_file:
           exportar_csv(trabalhos, csv_file)
           typer.echo(f"Dados exportados para {csv_file}")
           return
       
        typer.echo(json.dumps(trabalhos, indent=2, ensure_ascii=False))
        

    except requests.RequestException as erro:
        typer.echo(f"Erro ao aceder à API: {erro}", err=True)
        
#b
SEARCH_API_URL = "https://api.itjobs.pt/job/search.json"

@app.command("search")
def procurar_part_time(
    localidade: str = typer.Argument(None, help="Localidade (ex.: Porto)"),
    empresa: str = typer.Argument(None, help="Nome da empresa"),
    n: int = typer.Argument(10, help="Número de trabalhos a listar"),
):
    """Procura trabalhos part-time por localidade e/ou empresa"""
    
    # Build URL with only the filters provided
    url = f"{SEARCH_API_URL}?type=2&limit={n}&api_key={API_KEY}"
    
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        todos_trabalhos = response.json().get("results", [])
        
        # Aplicar filtros localmente
        trabalhos_filtrados = []
        
        for trabalho in todos_trabalhos:
            passar = True
            
            # Filtrar por localidade
            if localidade and localidade.lower() != "none":
                trabalho_location = trabalho.get("location")
                trabalho_localidade = ""
                
                # Se location for um dicionário, pega o nome
                if isinstance(trabalho_location, dict):
                    trabalho_localidade = trabalho_location.get("name", "")
                # Se location for uma string, usa diretamente
                elif isinstance(trabalho_location, str):
                    trabalho_localidade = trabalho_location
                # Se for None ou outro tipo, usa string vazia
                else:
                    trabalho_localidade = ""
                
                if localidade.lower() not in trabalho_localidade.lower():
                    passar = False
            
            # Filtrar por empresa (só se ainda passar o filtro de localidade)
            if passar and empresa and empresa.lower() != "none":
                trabalho_empresa = trabalho.get("company", {}).get("name", "")
                if trabalho_empresa and empresa.lower() not in trabalho_empresa.lower():
                    passar = False
            
            if passar:
                trabalhos_filtrados.append(trabalho)
        
        # Limitar ao número pedido após filtragem
        trabalhos_filtrados = trabalhos_filtrados[:n]

        if not trabalhos_filtrados:
            typer.echo("Nenhum trabalho part-time encontrado com esses critérios.")
            return

        # Mostrar em formato JSON
        typer.echo(json.dumps(trabalhos_filtrados, indent=2, ensure_ascii=False))
        typer.echo(f"\nEncontrados {len(trabalhos_filtrados)} trabalhos")

    except requests.RequestException as erro:
        typer.echo(f"Erro ao aceder à API: {erro}", err=True)


#c        
GET_API_URL = "https://api.itjobs.pt/job/get.json"

def determinar_regime(job):
    """Determina o regime de trabalho usando regex e campos da API"""
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


#d
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
        
        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d")
        
        trabalhos_filtrados = [
            t for t in trabalhos 
            if t.get("publishedAt") and 
            dt_inicio <= datetime.strptime(t["publishedAt"].split(" ")[0].split("T")[0], "%Y-%m-%d") <= dt_fim
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

def exportar_csv(trabalhos, filename):
    """Exporta trabalhos para um ficheiro CSV"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['titulo', 'empresa', 'descricao', 'data_publicacao', 'salario', 'localizacao']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for trabalho in trabalhos:
            writer.writerow({
                'titulo': trabalho.get('title', 'N/A'),
                'empresa': trabalho.get('company', {}).get('name', 'N/A'),
                'descricao': trabalho.get('body', 'N/A')[:200] + '...',
                'data_publicacao': trabalho.get('publishedAt', 'N/A'),
                'salario': trabalho.get('wage', 'N/A'),
                'localizacao': trabalho.get('location', 'N/A')
            })


if __name__ == "__main__":
    app()