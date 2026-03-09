from core.pipeline import PIIManager
import time


def test_masking():
    print("--- Initializing Manager (Model Loading) ---")
    start_load = time.time()
    manager = PIIManager()  # Premier chargement (plus lent)
    print(f"Load Time: {time.time() - start_load:.4f}s")

    text_input = "Salut, je suis Arnaud, mon mail est arnaud@dofus.com et j'habite à Paris."

    print("\n--- Processing Text (Execution) ---")
    start_proc = time.time()
    result = manager.mask_text(text_input)
    print(f"Process Time: {time.time() - start_proc:.4f}s")

    print("\n--- Result ---")
    print(f"Original: {text_input}")
    print(f"Masked:   {result}")

    # Vérification du cache (Singleton)
    print("\n--- Second Call (Should be instant) ---")
    start_proc2 = time.time()
    manager2 = PIIManager()  # Ne recharge PAS le modèle
    manager2.mask_text("Juste un test pour voir la vitesse.")
    print(f"2nd Process Time: {time.time() - start_proc2:.4f}s")


if __name__ == "__main__":
    test_masking()