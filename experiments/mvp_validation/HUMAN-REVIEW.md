# Human review

Marque uma opção por campo e escreva observações sem corrigir as fichas antes da avaliação.

Preenchido por: Eduardo — 2026-10-10

---

## Observação geral (aplica-se a TODAS as fichas)

**Faltam os nomes dos contatos nas Mentions.** As fichas trazem o autor como veio do
export — majoritariamente número de telefone (`+55 11 90000-0000`), e não o nome da
pessoa. Sem isso, a Mention perde justamente a informação que a torna útil: *quem*
recomendou. Vale para todas as fichas, sem exceção.

Isso é uma exigência de **identity resolution** (mapa `telefone → pessoa`), não de
arquitetura. O experimento não tentou resolver identidade — corretamente, conforme o
briefing. Mas a revisão humana revela que isso é requisito, não luxo.

---

## LightRAG

Context accuracy: [x] good [ ] acceptable [ ] bad

Capabilities quality: [x] good [ ] acceptable [ ] bad

Would I want this in my knowledge base?
[x] yes
[ ] maybe
[ ] no

Comments: I need the names of contacts in mention. Same for all.

## LEANN

Context accuracy: [x] good [ ] acceptable [ ] bad

Capabilities quality: [x] good [ ] acceptable [ ] bad

Would I want this in my knowledge base?
[x] yes
[ ] maybe
[ ] no

Comments: (faltam nomes de contatos — ver observação geral)

## gitingest

Context accuracy: [x] good [ ] acceptable [ ] bad

Capabilities quality: [x] good [ ] acceptable [ ] bad

Would I want this in my knowledge base?
[x] yes
[ ] maybe
[ ] no

Comments: (faltam nomes de contatos — ver observação geral)

## evaluate-rag

Context accuracy: [x] good [ ] acceptable [ ] bad

Capabilities quality: [x] good [ ] acceptable [ ] bad

Would I want this in my knowledge base?
[x] yes
[ ] maybe
[ ] no

Comments: (faltam nomes de contatos — ver observação geral)

## toon

Context accuracy: [x] good [ ] acceptable [ ] bad

Capabilities quality: [ ] good [x] acceptable [ ] bad

Would I want this in my knowledge base?
[x] yes
[ ] maybe
[ ] no

Comments: Description not clear. (faltam nomes de contatos — ver observação geral)
