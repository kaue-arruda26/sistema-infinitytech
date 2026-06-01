import sqlite3
import os

# Script para limpar o cliente travado no limbo do SQL
def rodar_limpeza():
    # Busca automática pelo arquivo .db na pasta do projeto
    arquivo_banco = None
    for arquivo in os.listdir('.'):
        if arquivo.endswith('.db') or arquivo.endswith('.sqlite'):
            arquivo_banco = arquivo
            break
            
    if not arquivo_banco:
        print("❌ Arquivo de banco de dados (.db) não encontrado na pasta atual.")
        return

    print(f"🔍 Banco de dados encontrado: {arquivo_banco}")
    conn = sqlite3.connect(arquivo_banco)
    cursor = conn.cursor()

    whatsapp_travado = "11988197532"

    try:
        # Remove de vez das duas tabelas para não restar dúvidas
        cursor.execute("DELETE FROM clientes WHERE whatsapp = ?", (whatsapp_travado,))
        cursor.execute("DELETE FROM atendimentos WHERE whatsapp = ?", (whatsapp_travado,))
        
        conn.commit()
        print(f"✨ SUCESSO: O WhatsApp {whatsapp_travado} foi totalmente removido!")
        print("👉 Pode voltar ao sistema, dar um F5 e cadastrá-lo novamente.")
        
    except Exception as e:
        print(f"❌ Erro ao executar a limpeza no SQL: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    rodar_limpeza()