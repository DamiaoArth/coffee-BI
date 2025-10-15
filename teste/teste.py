arquivo = "config/database.py"  # ou models/database_models.py
with open(arquivo, "rb") as f:
    conteudo = f.read()

for i, b in enumerate(conteudo):
    if b > 127:  # qualquer byte fora ASCII
        print(f"Byte suspeito {b:#04x} na posição {i}")
