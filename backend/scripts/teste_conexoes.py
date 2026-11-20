"""Teste de bancada da Etapa 1B: banco (Supabase) + IA (OpenCode Go).

Uso (na pasta backend):  uv run python scripts/teste_conexoes.py
"""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.services.checks import checar_banco, checar_ia  # noqa: E402
from app.services.llm import USER_AGENT, cliente_llm  # noqa: E402


def main() -> int:
    s = get_settings()
    falhou = False

    print("1) Banco de dados (Supabase)")
    banco = checar_banco(s)
    print("   ", banco)
    falhou |= banco["status"] != "ok"

    print("2) Modelos disponíveis no OpenCode Go")
    if s.llm_api_key:
        try:
            r = httpx.get(
                "https://opencode.ai/inference/go/v1/models",
                headers={"Authorization": f"Bearer {s.llm_api_key}", "User-Agent": USER_AGENT},
                timeout=15,
            )
            ids = sorted(m.get("id", "?") for m in r.json().get("data", [])) if r.is_success else []
            print(f"    HTTP {r.status_code}; {len(ids)} modelos; '{s.llm_model}' na lista: {s.llm_model in ids}")
        except Exception as e:  # noqa: BLE001
            print("    não foi possível listar:", type(e).__name__, str(e)[:150])
    else:
        print("    LLM_API_KEY vazia")

    print("3) Teste rápido da IA")
    ia = checar_ia(s)
    print("   ", ia)
    falhou |= ia["status"] != "ok"

    if ia["status"] == "ok":
        print("4) Ísis se apresentando")
        resp = cliente_llm(s, sessao="teste-bancada").responses.create(
            model=s.llm_model,
            instructions="Você é a Ísis, atendente virtual de uma clínica odontológica. Responda em português, em uma frase.",
            input="Olá! Quem é você?",
            max_output_tokens=120,
        )
        print("    Ísis:", (resp.output_text or "").strip())

    print("\nRESULTADO:", "❌ algo falhou (veja acima)" if falhou else "✅ banco e IA funcionando")
    return 1 if falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
