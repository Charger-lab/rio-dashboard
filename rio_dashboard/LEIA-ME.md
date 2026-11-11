# Rio Dashboard

Boletim do Trabalho (Novo CAGED) para o município do Rio de Janeiro, em Python.
Mesmos cálculos do dashboard em R: modelo oficial "com ajustes" (CAGEDMOV + CAGEDFOR − CAGEDEXC),
9 gráficos, 7 tabelas e PDF de 5 páginas.

## Como gerar o instalador para Windows (Rio-Dashboard-Instalador.exe)

O instalador precisa ser construído em um computador Windows. O GitHub faz isso de graça:

1. Crie uma conta em https://github.com (se ainda não tiver) e clique em **New repository**.
   Escolha um nome (ex.: `rio-dashboard`) e marque **Private**.
2. Na página do repositório, clique em **uploading an existing file** e arraste **todo o conteúdo**
   desta pasta (as pastas `rio_dashboard`, `assets`, `instalador`, `.github` e os arquivos soltos).
   - Se a pasta oculta `.github` não subir, clique em **Add file → Create new file**, digite
     `.github/workflows/instalador.yml` no nome e cole o conteúdo do arquivo de mesmo nome.
3. Clique em **Commit changes**.
4. Abra a aba **Actions**, escolha **Gerar instalador do Rio Dashboard (Windows)** e clique em **Run workflow**.
5. Espere uns 10 a 15 minutos. Quando ficar verde, abra a execução e baixe
   **Rio-Dashboard-Instalador** na seção *Artifacts* (vem em .zip; o instalador está dentro).
6. Se ficar vermelho, abra a execução, copie a mensagem de erro do passo que falhou e me envie.

O fluxo já roda um **autoteste** do programa empacotado (gráficos, PDF e leitura de .7z) antes de
criar o instalador. Se o autoteste falhar, nenhum instalador é gerado.

## Usar sem instalar (para testar, com Python 3.13)

    pip install -r requirements.txt
    python -m rio_dashboard

## Fontes de dados

- **FTP do MTE:** baixa os .7z direto do servidor oficial (modo rápido = até 4 downloads simultâneos).
- **Pasta no computador:** lê os .7z de uma pasta, por exemplo a do Google Drive para computador, ou uma
  pasta onde você baixou os arquivos. Os arquivos precisam ter o nome original (CAGEDMOV202609.7z...)
  e nunca são apagados.

Em ambos os casos o app guarda só as linhas do Rio (cerca de 1 MB por arquivo) em
`Rio Dashboard\dados` dentro da sua pasta de usuário, e apaga os arquivos pesados.
