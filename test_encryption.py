from encryption_utils import encrypt_answer, decrypt_answer

def test_encryption():
    original = "ma réponse secrète"
    encrypted = encrypt_answer(original)
    decrypted = decrypt_answer(encrypted)

    print("✅ Texte original :", original)
    print("🔐 Texte chiffré :", encrypted)
    print("🔓 Texte déchiffré :", decrypted)

    assert original == decrypted, "❌ Erreur : le texte déchiffré ne correspond pas à l'original"
    print("✅ Test réussi : chiffrement et déchiffrement fonctionnent correctement.")

if __name__ == "__main__":
    test_encryption()
