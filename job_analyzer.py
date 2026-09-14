from __future__ import annotations

import os
import re
import base64
from email.utils import parseaddr

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


# Fuentes que normalmente envían ofertas de empleo
JOB_SOURCES = [
    "linkedin.com",
    "computrabajo.com",
    "getonbrd.com",
    "freelancer.com",
    "indeed.com",
    "glassdoor.com",
    "bumeran.com",
    "elempleo.com",
    "peakU".lower(),

    # Plataformas ATS / reclutamiento
    "hire.lever.co",
    "lever.co",
    "greenhouse.io",
    "myworkday.com",
    "workday.com",
    "ashbyhq.com",
]


# Indicadores fuertes de que el correo contiene una oferta
OFFER_PATTERNS = [
    r"\bbusca personal\b",
    r"\bbusca[n]? candidatos?\b",
    r"\bvacante\b",
    r"\bvacantes\b",
    r"\bpuesto de\b",
    r"\bpuesto para\b",
    r"\boferta de empleo\b",
    r"\boferta laboral\b",
    r"\boportunidad laboral\b",
    r"\bempleo disponible\b",
    r"\btrabajo remoto\b",
    r"\bremote\b",
    r"\bfull.?stack developer\b",
    r"\bbackend developer\b",
    r"\bfrontend developer\b",
    r"\bsoftware engineer\b",
    r"\bsoftware developer\b",
    r"\bdesarrollador\b",
    r"\bprogramador\b",
    r"\bdeveloper\b",
    r"\bengineer\b",
]


# Indicadores de que YA existe una candidatura
APPLICATION_PATTERNS = [
    r"\bse ha enviado tu solicitud\b",
    r"\btu solicitud\b",
    r"\btu candidatura\b",
    r"\bseguimiento de tu candidatura\b",
    r"\bcandidatura avanza\b",
    r"\bpostulación\b",
    r"\bpostulacion\b",
    r"\baplicación\b",
    r"\baplicacion\b",
    r"\bhas aplicado\b",
    r"\byour application\b",
    r"\bapplication status\b",
    r"\bapplication submitted\b",
    r"\bapplication received\b",
    r"\bwe received your application\b",
    r"\bthank you for your application\b",
    r"\bthank you for applying\b",
    r"\bwe received your application for\b",
    r"\bresultados de pruebas\b",
    r"\bpasos a seguir\b",
]


# Tecnologías relevantes para el perfil
SKILLS = {
    "full stack": ["full stack", "fullstack"],
    "node.js": ["node.js", "node"],
    "typescript": ["typescript"],
    "javascript": ["javascript"],
    "php": ["php"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "react": ["react", "react.js"],
    "angular": ["angular"],
    "python": ["python"],
    ".net": [".net", "dotnet"],
    "c#": ["c#", "csharp"],
    "sql": ["sql"],
    "rest api": ["rest api", "restful"],
    "jwt": ["jwt"],
    "html": ["html"],
    "css": ["css"],
    "git": ["git"],
}


def authenticate():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(
                port=0,
                open_browser=True
            )

        with open("token.json", "w") as token:
            token.write(creds.to_json())

        os.chmod("token.json", 0o600)

    return creds


def decode_body(data):
    if not data:
        return ""

    try:
        return base64.urlsafe_b64decode(data).decode(
            "utf-8",
            errors="ignore"
        )
    except Exception:
        return ""


def extract_text(payload):
    text = ""

    if payload.get("body", {}).get("data"):
        text += decode_body(
            payload["body"]["data"]
        )

    for part in payload.get("parts", []):
        text += extract_text(part)

    return text


def get_header(headers, name):
    for header in headers:
        if header["name"].lower() == name.lower():
            return header["value"]

    return ""


def normalize(text):
    text = text.lower()

    # Elimina HTML básico
    text = re.sub(r"<[^>]+>", " ", text)

    # Normaliza espacios
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_domain(email):
    return email.split("@")[-1].lower()


def is_job_source(sender_email, body):
    sender_domain = get_domain(sender_email)

    for source in JOB_SOURCES:
        if source in sender_domain or source in body:
            return True

    return False


def has_non_job_signal(subject, body):
    """
    Detecta correos que no representan una oportunidad laboral.
    Se evalúa antes de aceptar una fuente laboral para evitar
    falsos positivos de notificaciones, conversaciones y correos
    administrativos.
    """
    text = normalize(subject + " " + body)
    subject_n = normalize(subject)

    non_job_patterns = [
        # SENA / formación
        "sena",
        "análisis y desarrollo de software",
        "analisis y desarrollo de software",
        "bienvenida y confirmación de inscripción",
        "confirmación de inscripción",
        "confirmacion de inscripcion",
        "formación titulada",
        "formacion titulada",

        # LinkedIn: notificaciones que no son ofertas
        "ha visitado tu perfil",
        "1 persona ha visitado tu perfil",
        "personas han visitado tu perfil",
        "tienes 1 invitación nueva",
        "tienes una invitación nueva",
        "invitación nueva",
        "invitacion nueva",
        "nueva conexión",
        "nueva conexion",

    ]

    # Una respuesta personal se descarta por el asunto.
    # No buscamos "re:" en todo el cuerpo para no eliminar
    # procesos laborales legítimos que incluyan contenido citado.
    if subject_n.startswith("re:"):
        return True

    return any(pattern in text for pattern in non_job_patterns)


def has_remote_signal(subject, body):
    """
    Detecta señales explícitas de trabajo remoto.
    No considera híbrido como remoto.
    """
    text = normalize(subject + " " + body)

    remote_patterns = [
        "remote",
        "remoto",
        "remota",
        "trabajo remoto",
        "empleo remoto",
        "puesto remoto",
        "vacante remota",
        "100% remoto",
        "100% remota",
        "fully remote",
        "fully remotely",
        "remote position",
        "remote job",
        "remote work",
        "work from home",
        "work-from-home",
        "home office",
        "teletrabajo",
        "teletrabajo 100%",
        "distributed team",
        "distributed",
    ]

    return any(pattern in text for pattern in remote_patterns)


def has_job_signal(subject, body):
    """
    Señales explícitas de una oportunidad o proceso laboral.
    """
    text = normalize(subject + " " + body)

    job_patterns = [
        # Vacantes
        "vacante",
        "vacantes",
        "oferta de empleo",
        "oferta laboral",
        "ofertas de empleo",
        "ofertas laborales",
        "puesto",
        "posición",
        "posicion",
        "empleo",
        "empleos",
        "job",
        "jobs",
        "job opportunity",
        "job alert",
        "employment",

        # Procesos de selección
        "candidatura",
        "candidatura enviada",
        "postulación",
        "postulacion",
        "application",
        "application submitted",
        "application received",
        "we received your application",
        "thank you for your application",
        "thank you for applying",
        "proceso de selección",
        "proceso de seleccion",
        "selección",
        "seleccion",
        "entrevista",
        "interview",
        "prueba técnica",
        "prueba tecnica",
        "technical test",
        "technical assessment",
        "coding challenge",
        "seguimiento de tu candidatura",
        "seguimiento de tu postulación",
    ]

    return any(pattern in text for pattern in job_patterns)


def has_offer_signal(subject, body):
    text = normalize(subject + " " + body)

    for pattern in OFFER_PATTERNS:
        if re.search(pattern, text):
            return True

    return False


def has_application_signal(subject, body):
    text = normalize(subject + " " + body)

    for pattern in APPLICATION_PATTERNS:
        if re.search(pattern, text):
            return True

    return False


def extract_skills(subject, body):
    text = normalize(subject + " " + body)

    found = []

    for skill, patterns in SKILLS.items():
        for pattern in patterns:
            if re.search(
                r"(?<!\w)" + re.escape(pattern) + r"(?!\w)",
                text
            ):
                found.append(skill)
                break

    return found


def extract_position(subject, body):
    subject_clean = re.sub(
        r"\s+",
        " ",
        subject
    ).strip()

    patterns = [
        r"puesto de (.+?)(?:\s*\(|$)",
        r"puesto para (.+?)(?:\s*\(|$)",
        r"vacante (.+?)(?:\s*\(|$)",
        r"puesto de (.+)",
        r"para el puesto de (.+)",
        r"para el puesto (.+)",
        r"busca personal para el puesto de (.+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            subject_clean,
            re.IGNORECASE
        )

        if match:
            position = match.group(1).strip()
            return position[:150]

    # Si el asunto contiene un cargo reconocible
    job_titles = [
        "backend software engineer",
        "backend developer",
        "frontend developer",
        "full stack developer",
        "fullstack developer",
        "software engineer",
        "software developer",
        "desarrollador",
        "developer",
        "programador",
        "engineer",
    ]

    lower_subject = subject_clean.lower()

    for title in job_titles:
        if title in lower_subject:
            index = lower_subject.find(title)
            return subject_clean[index:index + 120]

    return subject_clean[:120]


def extract_company(subject, sender_name, body):
    # Caso típico de LinkedIn:
    # "Empresa busca personal para..."
    match = re.search(
        r"^(.+?)\s+busca personal",
        subject,
        re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    match = re.search(
        r"^(.+?)\s+busca personal para",
        subject,
        re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    # Si no se pudo obtener desde el asunto,
    # usamos el nombre del remitente.
    if sender_name:
        return sender_name.strip()

    return "Empresa no identificada"


def extract_url(body):
    urls = re.findall(
        r"https?://[^\s<>\"']+",
        body
    )

    for url in urls:
        clean = url.rstrip(".,);]")

        if any(domain in clean.lower() for domain in [
            "linkedin.com/jobs",
            "linkedin.com/comm/jobs",
            "computrabajo.com",
            "getonbrd.com/empleos",
            "freelancer.com",
            "indeed.com",
            "glassdoor.com",
            "elempleo.com",
        ]):
            return clean

    return urls[0].rstrip(".,);]") if urls else ""


def calculate_score(skills, subject, body):
    text = normalize(subject + " " + body)

    score = 0

    # Tecnologías principales del perfil
    priority = {
        "python": 15,
        "full stack": 15,
        "javascript": 10,
        "typescript": 10,
        "react": 10,
        "node.js": 10,
        "php": 8,
        "sql": 7,
        "mysql": 7,
        "rest api": 7,
        "mongodb": 5,
        "c#": 5,
        ".net": 5,
        "jwt": 4,
        "git": 3,
        "html": 2,
        "css": 2,
        "angular": 3,
    }

    for skill in skills:
        score += priority.get(skill, 2)

    # Modalidad remota
    if "remote" in text or "remoto" in text:
        score += 8

    # Nivel compatible
    if "junior" in text:
        score += 8

    if "trainee" in text:
        score += 5

    # Penalizar experiencia claramente superior
    if re.search(r"\b[5-9]\+? años?\b", text):
        score -= 15

    if "senior" in text:
        score -= 15

    return max(0, min(score, 100))

def classify(score):
    if score >= 60:
        return "ALTA"

    if score >= 35:
        return "MEDIA"

    return "BAJA"


def get_messages(service, max_results=50):
    response = service.users().messages().list(
        userId="me",
        q="newer_than:14d",
        maxResults=max_results
    ).execute()

    return response.get("messages", [])


def read_message(service, message_id):
    message = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    subject = get_header(headers, "Subject")
    sender = get_header(headers, "From")
    date = get_header(headers, "Date")

    sender_name, sender_email = parseaddr(sender)

    body = extract_text(payload)

    return {
        "id": message_id,
        "subject": subject,
        "sender_name": sender_name,
        "sender_email": sender_email,
        "date": date,
        "body": body,
        "labels": message.get("labelIds", []),
    }


def analyze(data):
    subject = data["subject"]
    body = data["body"]
    sender_email = data["sender_email"]

    # PRIMER FILTRO:
    # solo fuentes relacionadas con empleo
    if not is_job_source(sender_email, body):
        return None

    # SEGUNDO FILTRO:
    # descartar correos administrativos, personales y
    # notificaciones que no representan un proceso laboral.
    if has_non_job_signal(subject, body):
        return None

    # TERCER FILTRO:
    # descartamos candidaturas ya enviadas
    if has_application_signal(subject, body):
        return None

    # TERCER FILTRO:
    # debe existir una señal real de oferta
    if not has_offer_signal(subject, body):
        return None

    skills = extract_skills(subject, body)

    score = calculate_score(
        skills,
        subject,
        body
    )

    return {
        "subject": subject,
        "company": extract_company(
            subject,
            data["sender_name"],
            body
        ),
        "position": extract_position(
            subject,
            body
        ),
        "source": get_domain(sender_email),
        "sender": data["sender_name"] or sender_email,
        "date": data["date"],
        "skills": skills,
        "score": score,
        "classification": classify(score),
        "url": extract_url(body),
    }


def main():
    print("=" * 70)
    print("GMAIL JOB ASSISTANT")
    print("FILTRO DE OFERTAS DE EMPLEO")
    print("=" * 70)
    print()

    service = build(
        "gmail",
        "v1",
        credentials=authenticate()
    )

    print("Analizando correos...")
    print()

    messages = get_messages(service)

    offers = []

    for message in messages:
        data = read_message(
            service,
            message["id"]
        )

        result = analyze(data)

        if result:
            offers.append(result)

    offers.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    print("=" * 70)
    print(f"OFERTAS SELECCIONADAS: {len(offers)}")
    print("=" * 70)
    print()

    for index, offer in enumerate(offers, start=1):

        print(
            f"#{index} "
            f"[{offer['classification']}] "
            f"{offer['score']}%"
        )

        print(
            f"Cargo     : {offer['position']}"
        )

        print(
            f"Empresa   : {offer['company']}"
        )

        print(
            f"Fuente    : {offer['source']}"
        )

        print(
            f"Fecha     : {offer['date']}"
        )

        print(
            "Tecnologías: "
            + (
                ", ".join(offer["skills"])
                if offer["skills"]
                else "No detectadas"
            )
        )

        if offer["url"]:
            print(
                f"URL       : {offer['url']}"
            )

        print("-" * 70)

    high = sum(
        1 for offer in offers
        if offer["classification"] == "ALTA"
    )

    medium = sum(
        1 for offer in offers
        if offer["classification"] == "MEDIA"
    )

    low = sum(
        1 for offer in offers
        if offer["classification"] == "BAJA"
    )

    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"ALTA       : {high}")
    print(f"MEDIA      : {medium}")
    print(f"BAJA       : {low}")
    print(f"TOTAL      : {len(offers)}")
    print("=" * 70)


if __name__ == "__main__":
    main()

def classify_work_mode(subject, body):
    """
    Clasifica la modalidad laboral detectada en el correo.

    Valores:
    - REMOTO
    - HIBRIDO
    - PRESENCIAL
    - NO_DEFINIDO
    - ADMISION
    """
    text = normalize(subject + " " + body)

    hybrid_patterns = [
        "hybrid",
        "hibrido",
        "híbrido",
        "hibrida",
        "híbrida",
        "trabajo híbrido",
        "trabajo hibrido",
        "modelo híbrido",
        "modelo hibrido",
    ]

    remote_patterns = [
        "100% remoto",
        "100% remota",
        "fully remote",
        "remote position",
        "remote job",
        "remote work",
        "work from home",
        "work-from-home",
        "home office",
        "trabajo remoto",
        "empleo remoto",
        "puesto remoto",
        "vacante remota",
        "teletrabajo",
        "teletrabajo 100%",
        "remote",
        "remoto",
        "remota",
        "distributed team",
        "distributed",
    ]

    onsite_patterns = [
        "presencial",
        "on-site",
        "on site",
        "onsite",
        "trabajo presencial",
        "oficina",
        "office based",
        "in office",
    ]

    if any(pattern in text for pattern in hybrid_patterns):
        return "HIBRIDO"

    if any(pattern in text for pattern in remote_patterns):
        return "REMOTO"

    if any(pattern in text for pattern in onsite_patterns):
        return "PRESENCIAL"

    return "NO_DEFINIDO"
