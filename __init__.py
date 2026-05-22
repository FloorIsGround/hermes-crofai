"""CrofAI — powerful models, crazy cheap pricing. OpenAI-compatible inference."""
from providers import register_provider
from providers.base import ProviderProfile

crofai = ProviderProfile(
    name="crofai",
    aliases=("crof", "crof-ai"),
    display_name="CrofAI",
    description="CrofAI — powerful models, crazy cheap pricing",
    signup_url="https://crof.ai/signin",
    env_vars=("CROFAI_API_KEY",),
    base_url="https://crof.ai/v1",
    auth_type="api_key",
    default_aux_model="deepseek-v4-flash",
    fallback_models=(
        "deepseek-v4-pro",
        "deepseek-v4-flash",
        "deepseek-v3.2",
        "kimi-k2.6",
        "glm-5.1",
        "gemma-4-31b-it",
        "minimax-m2.5",
        "qwen3.5-397b-a17b",
    ),
)

register_provider(crofai)
