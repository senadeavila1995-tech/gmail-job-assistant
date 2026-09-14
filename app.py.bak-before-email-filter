from flask import Flask, render_template
from googleapiclient.discovery import build

from job_analyzer import (
    authenticate,
    get_messages,
    read_message,
    analyze,
)

app = Flask(__name__)

STATUS_CONFIG = {
    "ENTREVISTA": {
        "title": "Entrevistas",
        "icon": "🎤",
        "class": "interview",
        "priority": 100,
    },
    "ADMISION": {
        "title": "Admisión / Selección",
        "icon": "🎉",
        "class": "admission",
        "priority": 95,
    },
    "PRUEBA": {
        "title": "Pruebas",
        "icon": "🧪",
        "class": "test",
        "priority": 80,
    },
    "SEGUIMIENTO": {
        "title": "Seguimiento",
        "icon": "👀",
        "class": "followup",
        "priority": 60,
    },
    "APLICADA": {
        "title": "Aplicaciones",
        "icon": "📝",
        "class": "application",
        "priority": 40,
    },
    "OFERTA": {
        "title": "Ofertas nuevas",
        "icon": "🟢",
        "class": "offer",
        "priority": 30,
    },
    "RECHAZADA": {
        "title": "Rechazadas",
        "icon": "❌",
        "class": "rejected",
        "priority": 10,
    },
}


def normalize(text):
    return " ".join((text or "").lower().split())


def classify_status(subject, body):
    """
    Clasifica el estado del proceso laboral.

    El asunto tiene prioridad sobre el cuerpo porque portales como
    LinkedIn agregan mucho contenido automático en el cuerpo.
    """

    subject_n = normalize(subject)
    body_n = normalize(body)

    # ---------------------------------------------------------
    # 1. RECHAZADA
    # ---------------------------------------------------------
    rejection_subject = [
        "no has sido seleccionado",
        "no fuiste seleccionado",
        "no hemos seleccionado",
        "no continuaremos",
        "candidatura no seleccionada",
        "application rejected",
        "application unsuccessful",
        "we decided not to move forward",
        "we will not be moving forward",
    ]

    if any(x in subject_n for x in rejection_subject):
        return "RECHAZADA"

    # ---------------------------------------------------------
    # 2. ENTREVISTA
    # ---------------------------------------------------------
    interview_subject = [
        "entrevista",
        "interview",
        "entrevista técnica",
        "technical interview",
        "video interview",
        "phone interview",
        "screening interview",
        "agenda tu entrevista",
        "agendar entrevista",
        "programar entrevista",
        "schedule an interview",
        "invite you to interview",
    ]

    if any(x in subject_n for x in interview_subject):
        return "ENTREVISTA"

    # Solo buscamos señales fuertes en el cuerpo.
    interview_body = [
        "te invitamos a una entrevista",
        "te invitamos para una entrevista",
        "queremos entrevistarte",
        "nos gustaría entrevistarte",
        "hemos programado una entrevista",
        "schedule your interview",
        "we'd like to interview you",
        "we would like to interview you",
        "interview invitation",
    ]

    if any(x in body_n for x in interview_body):
        return "ENTREVISTA"

    # ---------------------------------------------------------
    # 3. PRUEBA
    # ---------------------------------------------------------
    test_subject = [
        "prueba técnica",
        "prueba tecnica",
        "technical test",
        "technical assessment",
        "assessment",
        "coding test",
        "coding challenge",
        "resultados de pruebas",
        "resultado de pruebas",
        "test técnico",
        "test tecnico",
    ]

    if any(x in subject_n for x in test_subject):
        return "PRUEBA"

    test_body = [
        "te hemos enviado una prueba técnica",
        "te hemos enviado una prueba",
        "completa la prueba técnica",
        "complete the technical test",
        "technical assessment",
        "coding challenge",
        "resultados de tus pruebas",
    ]

    if any(x in body_n for x in test_body):
        return "PRUEBA"

    # ---------------------------------------------------------
    # 4. ADMISIÓN / SELECCIÓN
    # ---------------------------------------------------------
    # MUY IMPORTANTE:
    # "hiring", "busca personal", "vacante", "job", "empleo"
    # NO significan que el usuario haya sido seleccionado.
    admission_subject = [
        "has sido seleccionado",
        "has sido seleccionada",
        "fuiste seleccionado",
        "fuiste seleccionada",
        "seleccionado para el cargo",
        "seleccionada para el cargo",
        "seleccionado para el puesto",
        "seleccionada para el puesto",
        "felicitaciones, has sido seleccionado",
        "felicitaciones, has sido seleccionada",
        "oferta de contratación",
        "oferta laboral para ti",
        "job offer for you",
        "you have been selected",
        "you've been selected",
        "we selected you",
        "we've selected you",
        "congratulations, you've been selected",
    ]

    if any(x in subject_n for x in admission_subject):
        return "ADMISION"

    admission_body = [
        "has sido seleccionado para continuar",
        "has sido seleccionada para continuar",
        "fuiste seleccionado para continuar",
        "fuiste seleccionada para continuar",
        "hemos decidido seleccionarte",
        "hemos decidido contratarte",
        "queremos ofrecerte el puesto",
        "queremos ofrecerte el cargo",
        "we have selected you",
        "we have decided to hire you",
        "we would like to offer you the position",
        "we'd like to offer you the position",
    ]

    if any(x in body_n for x in admission_body):
        return "ADMISION"

    # ---------------------------------------------------------
    # 5. SEGUIMIENTO
    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # 5. APLICADA
    # ---------------------------------------------------------
    # Confirmaciones de que la candidatura fue recibida/enviada.
    # Estas reglas deben evaluarse ANTES de seguimiento.
    applied_subject = [
        "candidatura enviada",
        "postulación enviada",
        "solicitud enviada",
        "hemos recibido tu candidatura",
        "hemos recibido tu postulación",
        "application submitted",
        "application received",
        "we received your application",
        "thank you for your application",
        "thank you for applying",
        "your application has been received",
        "tu solicitud ha sido enviada",
    ]

    if any(x in subject_n for x in applied_subject):
        return "APLICADA"

    applied_body = [
        "hemos recibido tu candidatura",
        "hemos recibido tu postulación",
        "hemos recibido tu solicitud",
        "we received your application",
        "thank you for your application",
        "thank you for applying",
        "your application has been received",
        "application received",
        "application submitted",
    ]

    if any(x in body_n for x in applied_body):
        return "APLICADA"

    # ---------------------------------------------------------
    # 6. SEGUIMIENTO
    # ---------------------------------------------------------
    followup_subject = [
        "seguimiento de tu candidatura",
        "seguimiento de tu postulación",
        "actualización de tu candidatura",
        "actualización de tu postulación",
        "tu candidatura avanza",
        "tu postulación avanza",
        "application update",
        "application status",
        "update on your application",
        "proceso de selección",
    ]

    if any(x in subject_n for x in followup_subject):
        return "SEGUIMIENTO"

    # ---------------------------------------------------------
    # 7. OFERTA
    # ---------------------------------------------------------
    offer_subject = [
        "busca personal para el puesto",
        "busca personal para",
        "nuevos empleos",
        "nuevas ofertas",
        "nuevas vacantes",
        "ofertas de empleo",
        "oferta de empleo",
        "empleos similares",
        "empleos que podrían interesarte",
        "empleos que podrian interesarte",
        "vacante",
        "puesto de",
        "job alert",
        "job alerts",
        "new jobs",
        "jobs you may be interested in",
        "similar jobs",
        "hiring",
        "we're hiring",
        "we are hiring",
        "perfect match",
    ]

    if any(x in subject_n for x in offer_subject):
        return "OFERTA"

    # Señales de oferta en cuerpo solamente cuando no existe
    # ninguna señal de proceso activo.
    offer_body = [
        "está buscando personal",
        "busca personal",
        "aplica ahora",
        "apply now",
        "postúlate",
        "postulate",
        "vacante disponible",
        "posición disponible",
        "position available",
    ]

    if any(x in body_n for x in offer_body):
        return "OFERTA"

    return None


def analyze_email(service, message_id):
    try:
        data = read_message(service, message_id)

        subject = data.get("subject", "")
        body = data.get("body", "")
        sender_name = data.get("sender_name", "")
        sender_email = data.get("sender_email", "")

        status = classify_status(subject, body)

        # -----------------------------------------------------
        # Analizador normal
        # -----------------------------------------------------
        analyzed = analyze(data)

        # -----------------------------------------------------
        # Las confirmaciones de candidatura también son
        # oportunidades laborales válidas.
        # -----------------------------------------------------
        if status == "APLICADA":
            import re

            text = f"{subject} {body}"

            # Empresa: normalmente viene en el nombre del remitente.
            company = sender_name.strip() if sender_name else ""

            if not company:
                company = "Empresa no identificada"

            # -------------------------------------------------
            # Extraer cargo desde frases típicas de ATS.
            # Ejemplo:
            # "we received your application for React Engineer..."
            # -------------------------------------------------
            position = ""

            position_patterns = [
                # Caso típico de Lever:
                # "we received your application for React Engineer - Remote,
                # Latin America, and we are delighted..."
                r"received your application for\s+(.+?),\s+and we\b",
                r"application for\s+(.+?),\s+and we\b",
                r"applied for\s+(.+?),\s+and we\b",
                r"application for the position of\s+(.+?),\s+and we\b",
                r"application for the role of\s+(.+?),\s+and we\b",
            ]

            for pattern in position_patterns:
                match = re.search(
                    pattern,
                    text,
                    re.IGNORECASE
                )

                if match:
                    position = re.sub(
                        r"\\s+",
                        " ",
                        match.group(1)
                    ).strip()

                    position = position.rstrip(",")
                    break

            # Fallback: intentar encontrar un título técnico.
            if not position:
                title_patterns = [
                    r"React Engineer[^<.!?]*",
                    r"Software Engineer[^<.!?]*",
                    r"Frontend Developer[^<.!?]*",
                    r"Backend Developer[^<.!?]*",
                    r"Full Stack Developer[^<.!?]*",
                    r"Fullstack Developer[^<.!?]*",
                    r"Software Developer[^<.!?]*",
                    r"Developer[^<.!?]*",
                ]

                for pattern in title_patterns:
                    match = re.search(
                        pattern,
                        text,
                        re.IGNORECASE
                    )

                    if match:
                        position = re.sub(
                            r"\\s+",
                            " ",
                            match.group(0)
                        ).strip()
                        break

            if not position:
                position = subject.strip()

            # -------------------------------------------------
            # Score de candidatura
            # -------------------------------------------------
            try:
                from job_analyzer import (
                    extract_skills,
                    calculate_score,
                    classify,
                )

                skills = extract_skills(
                    subject,
                    body
                )

                score = calculate_score(
                    skills,
                    subject,
                    body
                )

                classification = classify(score)

            except Exception:
                skills = []
                score = 0
                classification = "SIN CLASIFICAR"

            result = {
                "id": message_id,
                "status": status,
                "status_config": STATUS_CONFIG[status],
                "subject": subject,
                "company": company,
                "position": position[:150],
                "source": sender_email.split("@")[-1].lower()
                    if "@" in sender_email
                    else "",
                "sender": sender_name or sender_email,
                "sender_email": sender_email,
                "date": data.get("date", ""),
                "body": body,
                "skills": skills,
                "score": score,
                "classification": classification,
                "url": "",
                "gmail_url": (
                    "https://mail.google.com/mail/u/0/#all/"
                    + message_id
                ),
            }

            return result

        # -----------------------------------------------------
        # Oportunidades normales
        # -----------------------------------------------------
        if not status and not analyzed:
            return None

        if not status:
            status = "OFERTA"

        result = analyzed or {}

        result.update({
            "id": message_id,
            "status": status,
            "status_config": STATUS_CONFIG[status],
            "subject": subject,
            "sender": sender_name or sender_email,
            "sender_email": sender_email,
            "date": data.get("date", ""),
            "source": data.get("source") or "",
            "body": body,
            "gmail_url": (
                "https://mail.google.com/mail/u/0/#all/"
                + message_id
            ),
        })

        return result

    except Exception as exc:
        print(f"Error procesando {message_id}: {exc}")
        return None


@app.route("/")
def dashboard():
    opportunities = []
    error = None

    try:
        service = build(
            "gmail",
            "v1",
            credentials=authenticate()
        )

        messages = get_messages(
            service,
            max_results=50
        )

        seen_ids = set()

        for message in messages:
            message_id = message.get("id")

            if not message_id or message_id in seen_ids:
                continue

            seen_ids.add(message_id)

            result = analyze_email(
                service,
                message_id
            )

            if result:
                opportunities.append(result)

        opportunities.sort(
            key=lambda item: (
                -STATUS_CONFIG[item["status"]]["priority"],
                -item.get("score", 0),
                item.get("date", ""),
            )
        )

    except Exception as exc:
        error = str(exc)

    grouped = {
        status: []
        for status in STATUS_CONFIG
    }

    for item in opportunities:
        grouped[item["status"]].append(item)

    # Ordenar cada sección por fecha: más reciente primero.
    from email.utils import parsedate_to_datetime

    def sort_by_date(item):
        date_value = item.get("date", "")

        try:
            return parsedate_to_datetime(date_value).timestamp()
        except Exception:
            return 0

    for status in grouped:
        grouped[status].sort(
            key=sort_by_date,
            reverse=True,
        )

    stats = {
        status: len(grouped[status])
        for status in STATUS_CONFIG
    }

    return render_template(
        "index.html",
        opportunities=opportunities,
        grouped=grouped,
        stats=stats,
        status_config=STATUS_CONFIG,
        error=error,
    )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
