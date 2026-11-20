"""Operação do WhatsApp (WAHA) por clínica — substitui a tela do admin geral até a Etapa 7 (D31).

Uso (na pasta backend):
    uv run python scripts/whatsapp.py sessoes                      # sessões que existem no servidor WAHA
    uv run python scripts/whatsapp.py ligar demo <sessao>          # liga a clínica (slug) a uma sessão
    uv run python scripts/whatsapp.py status demo                  # status da sessão e webhooks atuais
    uv run python scripts/whatsapp.py qr demo                      # salva o QR code em qr-<sessao>.png
    uv run python scripts/whatsapp.py webhook demo                 # mostra o que vai mudar (não altera nada)
    uv run python scripts/whatsapp.py webhook demo --confirmar     # aponta o webhook da sessão para o nosso backend
"""

import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.canais.waha import ClienteWaha, WahaErro  # noqa: E402
from app.config import get_settings  # noqa: E402


def _clinica(conn, slug: str):
    r = conn.execute("select id, name from clinics where slug = %s", (slug,)).fetchone()
    if not r:
        raise SystemExit(f"Clínica '{slug}' não encontrada.")
    return r


def _sessao(conn, slug: str) -> str:
    cid, _ = _clinica(conn, slug)
    r = conn.execute("select session from whatsapp_instances where clinic_id = %s", (cid,)).fetchone()
    if not r:
        raise SystemExit(f"Clínica '{slug}' ainda não tem sessão. Rode: whatsapp.py ligar {slug} <sessao>")
    return r[0]


def _webhooks(info: dict) -> list[str]:
    return [w.get("url", "?") + "  eventos=" + ",".join(w.get("events") or []) for w in (info.get("config") or {}).get("webhooks") or []]


def main(args: list[str]) -> int:
    if not args:
        print(__doc__)
        return 1
    s = get_settings()
    cmd = args[0]
    waha = ClienteWaha(s)

    if cmd == "sessoes":
        for x in waha._req("GET", "/api/sessions", params={"all": "true"}).json():
            print(f"- {x.get('name')}: {x.get('status')}  número={((x.get('me') or {}).get('id'))}")
        return 0

    with psycopg.connect(s.database_url) as conn:
        if cmd == "ligar" and len(args) == 3:
            cid, nome = _clinica(conn, args[1])
            info = waha.sessao(args[2])  # confere se a sessão existe no WAHA
            conn.execute(
                """insert into whatsapp_instances (clinic_id, session, status) values (%s, %s, %s)
                   on conflict (clinic_id) do update set session = excluded.session, status = excluded.status, updated_at = now()""",
                (cid, args[2], info.get("status") or "DESCONHECIDO"),
            )
            conn.commit()
            print(f"✅ {nome} ligada à sessão '{args[2]}' (status {info.get('status')}).")
            return 0

        if cmd == "status" and len(args) == 2:
            sessao = _sessao(conn, args[1])
            info = waha.sessao(sessao)
            print(f"Sessão: {sessao}\nStatus: {info.get('status')}\nNúmero: {(info.get('me') or {}).get('id')}")
            print("Webhooks atuais:", *(_webhooks(info) or ["(nenhum)"]), sep="\n  ")
            return 0

        if cmd == "qr" and len(args) == 2:
            sessao = _sessao(conn, args[1])
            arq = Path(f"qr-{sessao}.png")
            arq.write_bytes(waha.qr_png(sessao))
            print(f"QR salvo em {arq.resolve()} — abra e leia com o WhatsApp do celular da clínica (vale ~60 s).")
            return 0

        if cmd == "webhook" and len(args) in (2, 3):
            if not (s.public_base_url and s.waha_webhook_hmac_key):
                raise SystemExit("Preencha PUBLIC_BASE_URL e WAHA_WEBHOOK_HMAC_KEY no backend/.env.")
            sessao = _sessao(conn, args[1])
            url = s.public_base_url.rstrip("/") + "/webhooks/waha"
            info = waha.sessao(sessao)
            print(f"Sessão '{sessao}'. Webhooks atuais:", *(_webhooks(info) or ["(nenhum)"]), sep="\n  ")
            print(f"Novo webhook (substitui os atuais): {url}  eventos=message,session.status  (assinado com HMAC)")
            if "--confirmar" not in args:
                print("\nNada foi alterado. Para aplicar, rode de novo com --confirmar.")
                return 0
            waha.configurar_webhook(sessao, url, s.waha_webhook_hmac_key)
            print("✅ Webhook atualizado. A sessão pode reiniciar por alguns segundos.")
            return 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except WahaErro as e:
        raise SystemExit(f"❌ {e}") from None
