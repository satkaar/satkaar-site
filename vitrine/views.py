from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

from .forms import ContactForm


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = kwargs.get("form") or ContactForm()
        return ctx

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        if form.is_valid():
            obj = form.save()
            _notify_contact(obj)
            messages.success(
                request,
                "Merci, votre message a bien été envoyé. Nous revenons vers vous sous 48 h.",
            )
            return redirect(reverse("home") + "#contact-merci")
        return self.render_to_response(self.get_context_data(form=form))


class MentionsLegalesView(TemplateView):
    template_name = "mentions_legales.html"


def _notify_contact(obj):
    """Envoie un email à l'adresse de contact pour chaque nouveau message."""
    subject = f"[satkaar.fr] Nouveau message de {obj.nom} ({obj.commune})"
    body = (
        f"Nom        : {obj.nom}\n"
        f"Fonction   : {obj.fonction}\n"
        f"Commune    : {obj.commune}\n"
        f"Email      : {obj.email}\n"
        f"Téléphone  : {obj.telephone or '—'}\n"
        f"Reçu le    : {obj.cree_le:%Y-%m-%d %H:%M}\n"
        f"\n"
        f"Message :\n{obj.message}\n"
    )
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.CONTACT_NOTIFICATION_EMAIL],
        reply_to=[obj.email],
    )
    try:
        email.send(fail_silently=True)
    except Exception:
        # Le message reste enregistré en base même si l'envoi échoue.
        pass


@require_GET
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Allow: /",
        "",
        f"Sitemap: {settings.SITE_URL.rstrip('/')}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def healthz(request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok"})
