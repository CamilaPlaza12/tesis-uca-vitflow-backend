import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

FROM_EMAIL = "VitFlow Onboarding <onboarding@vitflow.app>"


def send_new_onboarding_to_vitflow(req: dict):
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": "vitflow.information@gmail.com",
        "subject": "Nueva solicitud de hospital",
        "html": f"""
        <h3>Nueva solicitud</h3>
        <p><strong>Hospital:</strong> {req["hospital"]["name"]}</p>
        <p><strong>Email hospital:</strong> {req["hospital"]["email"]}</p>
        <p><strong>Admin:</strong> {req["admin"]["firstName"]} {req["admin"]["lastName"]}</p>
        <p><strong>Email admin:</strong> {req["admin"]["email"]}</p>
        """
    })


def send_onboarding_received_to_admin(req: dict):
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": req["admin"]["email"],
        "subject": "Recibimos tu solicitud - VitFlow",
        "html": f"""
        <p>Hola {req["admin"]["firstName"]},</p>
        <p>Recibimos tu solicitud para <strong>{req["hospital"]["name"]}</strong>.</p>
        <p>Te avisaremos dentro de las próximas 48hs.</p>
        """
    })


def send_onboarding_approved(req: dict, reset_link: str):
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": req["admin"]["email"],
        "subject": "Solicitud aprobada - Activá tu cuenta",
        "html": f"""
        <p>Hola {req["admin"]["firstName"]},</p>
        <p>Tu hospital <strong>{req["hospital"]["name"]}</strong> fue aprobado.</p>
        <p>Activá tu cuenta desde este link:</p>
        <a href="{reset_link}">Crear contraseña</a>
        """
    })


def send_onboarding_rejected(req: dict, review_note: str):
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": req["admin"]["email"],
        "subject": "Solicitud rechazada - VitFlow",
        "html": f"""
        <p>Hola {req["admin"]["firstName"]},</p>
        <p>No pudimos aprobar tu solicitud para <strong>{req["hospital"]["name"]}</strong>.</p>
        <p><strong>Motivo:</strong> {review_note}</p>
        """
    })
