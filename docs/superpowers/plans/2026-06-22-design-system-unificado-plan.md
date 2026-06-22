# BuszApp · Design System Unificado — Plano de Implementação

**Data:** 2026-06-22
**Spec:** `docs/superpowers/specs/2026-06-22-design-system-unificado-design.md` (commit `d8695a1`)
**Estratégia:** Big bang — fundação + 10 páginas no mesmo PR, em commits separados por bloco.

---

## Observações sobre o estado atual

Antes de começar, três coisas que descobri lendo o código:

1. **`static/js/app.js` já tem `Toast`** com `success/error/warning/info`. Não vamos criar `toast.js` separado — **refatoramos no lugar** e garantimos que o CSS dos toasts esteja em `main.css`.
2. **`static/css/main.css` já tem esqueleto de sidebar** (`.sidebar`, `.sidebar-item`, `.sidebar-logo`) — mantemos a base, ajustamos para o novo padrão.
3. **`static/js/header.js`** já tem API de `data-*` attributes para configurar título/subtítulo/ações — mantemos esta API e refatoramos o markup gerado.

Resultado: o spec mencionava 4 arquivos JS novos, mas na prática vai ser **2 arquivos JS novos** (`sidebar.js`, `bottom-nav.js`, `modal.js`) e **refator** de `header.js` + `app.js`. O `toast.js` separado deixa de fazer sentido.

> Esta diferença com a seção 5.1 do spec é proposital. Atualizar o spec depois que o plano for aprovado.

---

## Estrutura do PR

Um PR (`feat/design-system`) com 13 commits:

- 1 commit por sub-tarefa do **Bloco 1** (fundação)
- 1 commit por **página migrada** no Bloco 2
- 1 commit por **validação** no Bloco 3

Vantagem: revisão incremental, fácil reverter uma página específica sem perder o sistema, histórico legível.

---

## Bloco 1 — Fundação

**Definition of done do bloco:** abrir qualquer página existente continua funcionando exatamente como hoje. Nenhuma página foi migrada ainda. Mas a infra do design system está pronta para usar.

### 1.1 Reescrever `static/css/main.css` com tokens + classes do DS

- [ ] Substituir o bloco `:root` atual pelos tokens completos da seção 6 do spec (cores, gradientes, sombras, tipografia, espaçamento, raios, layout vars).
- [ ] Substituir o bloco `.dark` pelos overrides completos da seção 6.2.
- [ ] Manter as keyframes existentes (`fadeInUp`, `slideInLeft`, `slideInRight`, `scaleIn`, `float`, `pulse`, `spin`).
- [ ] Adicionar classes de componente: `.bz-btn` + modificadores, `.bz-input` + `.bz-input-wrap` + `.bz-label`, `.bz-badge` + modificadores, `.bz-card`, `.bz-stat-card`, `.bz-balance-card`, `.bz-item`, `.bz-tabs` + `.bz-tab`, `.bz-modal-overlay` + `.bz-modal-box` + `.bz-modal-title` + `.bz-modal-desc` + `.bz-modal-actions`.
- [ ] Renomear `.sidebar*` para `.bz-sidebar*` (alias antigos mantidos por 1 release para não quebrar nada durante a migração).
- [ ] Adicionar `.bz-header`, `.bz-bottom-nav` + `.bz-bottom-nav-item`.
- [ ] Adicionar `.toast-container` e `.toast` (cores das variantes via tokens).
- [ ] Validação: abrir o `dashboard.html` atual e confirmar que nada visualmente mudou ainda (só tokens novos).

**Commit:** `feat(design-system): adiciona tokens e classes de componentes em main.css`

### 1.2 Criar `static/js/sidebar.js`

- [ ] Helper que injeta a sidebar no DOM (similar ao padrão do `header.js`).
- [ ] API: `<script src="./js/sidebar.js" data-role="passageiro|motorista|admin"></script>` define qual conjunto de itens renderizar.
- [ ] Inclui logo no topo, lista de itens (configuração via objeto por role), botão "Sair" no rodapé.
- [ ] Highlight do item ativo com base em `window.location.pathname`.
- [ ] Drawer mobile: expõe `Sidebar.open()` / `Sidebar.close()`.

**Commit:** `feat(design-system): cria sidebar.js como componente compartilhado`

### 1.3 Criar `static/js/bottom-nav.js`

- [ ] Helper que injeta a bottom nav (mobile only — escondida por CSS no desktop).
- [ ] API: `<script src="./js/bottom-nav.js" data-role="passageiro|motorista|admin"></script>`.
- [ ] 5 itens (passageiro/motorista) ou 4 + "Mais" (admin) conforme tabela da seção 8 do spec.
- [ ] Highlight do item ativo por `window.location.pathname`.

**Commit:** `feat(design-system): cria bottom-nav.js`

### 1.4 Criar `static/js/modal.js`

- [ ] Helper que padroniza abrir/fechar modais usando as classes `.bz-modal-overlay`/`.bz-modal-box`.
- [ ] API mínima: `Modal.open(id)`, `Modal.close(id)`, `Modal.confirm({title, desc, onConfirm, onCancel})`.
- [ ] Fechar com ESC e clique no overlay.

**Commit:** `feat(design-system): cria modal.js com helper padronizado`

### 1.5 Refatorar `static/js/header.js`

- [ ] Manter a API atual de `data-*` para não quebrar páginas que ainda não foram migradas.
- [ ] Mudar o markup gerado para usar `.bz-header` (desktop branco) — o gradiente fica reservado pra versão mobile via media query no CSS.
- [ ] Garantir que o botão hamburger aparece só no mobile e dispara `Sidebar.open()`.

**Commit:** `refactor(design-system): header.js usa novas classes do DS`

### 1.6 Refatorar `Toast` em `static/js/app.js`

- [ ] Manter a API `Toast.success/error/warning/info`.
- [ ] Remover estilos inline do HTML do toast — usar `.toast` + modificadores do `main.css`.
- [ ] Ícones via Feather em vez de unicode (consistência com resto da UI).

**Commit:** `refactor(design-system): toasts usam classes do main.css`

### 1.7 Documentar uso em `static/css/README.md`

- [ ] Listar tokens disponíveis (referência rápida).
- [ ] Listar classes de componente com exemplos de markup.
- [ ] Convenções: usar Tailwind só para layout, classes `bz-*` para componentes.
- [ ] Como adicionar uma nova página (boilerplate).

**Commit:** `docs(design-system): adiciona guia de uso do DS`

---

## Bloco 2 — Migração das páginas

**Definition of done por página:**
- Nenhum `<style>` inline maior que 10 linhas (exceção: estilos de mapa/hero específicos da página).
- Header, sidebar e bottom-nav vêm dos helpers JS, sem markup duplicado.
- Botões, inputs, badges, cards, modais e tabs usam classes `.bz-*`.
- Light e dark mode visualmente OK.
- Comportamento funcional inalterado (clicks, navegação, forms, sockets).

**Ordem proposta:** dashboard primeiro (referência de qualidade), depois passageiro, depois motorista, depois admin.

### 2.1 `dashboard.html`

- [ ] Remover bloco `<style>` (mover regras genuinamente específicas pra final do main.css ou descartar).
- [ ] Trocar `<script src="./js/header.js" data-*>` por header já refatorado.
- [ ] Substituir `<nav class="sidebar">` inline pelo `<script src="./js/sidebar.js" data-role="passageiro">`.
- [ ] Adicionar `<script src="./js/bottom-nav.js" data-role="passageiro">`.
- [ ] Trocar `.balance-card`, `.action-btn`, `.tx-item`, `.modal-overlay`, `.modal-box` por classes `.bz-*`.
- [ ] Testar light/dark, mobile/desktop, login/logout.

**Commit:** `feat(design-system): migra dashboard.html`

### 2.2 `acompanhamento.html`

Mesmo padrão. Atenção a: integração Leaflet (manter estilos específicos do mapa em `<style>`).

**Commit:** `feat(design-system): migra acompanhamento.html`

### 2.3 `recarga.html`

Mesmo padrão. Atenção a: formulários de PIX/cartão, modal de QR code.

**Commit:** `feat(design-system): migra recarga.html`

### 2.4 `rating.html`

Mesmo padrão. Atenção a: componentes de estrelas (manter ou criar `.bz-stars` se reutilizar).

**Commit:** `feat(design-system): migra rating.html`

### 2.5 `profile.html`

Mesmo padrão. Atenção a: avatar com gradient ring, modais de edição.

**Commit:** `feat(design-system): migra profile.html`

### 2.6 `motorista.html`

Mesmo padrão. **Remover** as variáveis CSS próprias (`--bg`, `--accent`) — usar tokens do DS.

Atenção a: status dot pulsante (manter via `.bz-badge .dot` ou criar `.bz-status-dot` se for muito específico), socket.io em tempo real, layout do painel da cabine.

Sidebar usa `data-role="motorista"`.

**Commit:** `feat(design-system): migra motorista.html`

### 2.7 `admin.html`

Mesmo padrão. Atenção a: várias abas (`.admin-tab` → `.bz-tab`), múltiplos modais, mapa, chart.js.

Sidebar usa `data-role="admin"` — admin **ganha** sidebar (hoje não tem).

**Commit:** `feat(design-system): migra admin.html`

### 2.8 `admin-rotas.html`

Mesmo padrão. Atenção a: tabs de rota, pickers de mapa, lista de paradas com ordem.

**Commit:** `feat(design-system): migra admin-rotas.html`

### 2.9 `add-driver.html`

Mesmo padrão. Atenção a: validação de CPF/CNH, badges de status.

**Commit:** `feat(design-system): migra add-driver.html`

### 2.10 `add-vehicle.html`

Mesmo padrão.

**Commit:** `feat(design-system): migra add-vehicle.html`

---

## Bloco 3 — Validação

### 3.1 Smoke test light mode

- [ ] Servir o app local (`python -m src.main`) e abrir cada uma das 10 páginas.
- [ ] Checklist por página: header OK, sidebar abre/colapsa no desktop, bottom nav aparece no mobile, item ativo destacado, ações do header funcionam (notif, tema, perfil), modais abrem/fecham.

### 3.2 Smoke test dark mode

- [ ] Mesma checklist em dark, conferindo contraste de texto, sombras, cores semânticas (badges, alerts).

### 3.3 Audit de duplicação

- [ ] `grep -r "<style>" static/*.html` → cada match deve ter justificativa documentada no spec (mapas, hero animado).
- [ ] `grep -rE "form-input|modal-overlay|modal-box|stat-card|item-row|admin-tab|route-tab|driver-row|stop-row|btn-icon" static/*.html` → 0 matches (todas viraram `.bz-*`).

**Commit:** `test(design-system): valida light/dark em todas as 10 páginas`

### 3.4 Atualizar spec

- [ ] Editar seção 5.1 do spec pra remover `toast.js` (já existe em `app.js`).
- [ ] Marcar checklist da seção 10 como concluído.

**Commit:** `docs(design-system): atualiza spec após implementação`

---

## Ordem de execução resumida

```
1.1 main.css
1.2 sidebar.js
1.3 bottom-nav.js
1.4 modal.js
1.5 header.js refactor
1.6 toast refactor
1.7 README
2.1 dashboard
2.2 acompanhamento
2.3 recarga
2.4 rating
2.5 profile
2.6 motorista
2.7 admin
2.8 admin-rotas
2.9 add-driver
2.10 add-vehicle
3.1 smoke light
3.2 smoke dark
3.3 audit
3.4 spec update
```

## Pontos de atenção que podem mudar o plano

1. **Mudanças não commitadas pré-existentes:** o `git status` no início mostrou 22 arquivos modificados (HTMLs, main.css, app.js, header.js, main.py, auth.py etc.) que não vieram desta task. Confirmar com você antes de começar:
   - Estes diffs vão ser commitados antes? Ou eles fazem parte de outra coisa em andamento?
   - Se forem rascunhos, melhor stashar antes do bloco 1 pra não misturar.
2. **Branch:** o `git log` mostra trabalho direto em `main`. Sugiro criar branch `feat/design-system` antes de começar.
3. **Tailwind CDN em produção:** spec deixa explícito que isso fica, mas vale lembrar que o `cdn.tailwindcss.com` é oficialmente "para prototipagem". Se em algum momento a equipe quiser mover pra build local, o DS já está preparado (tokens em CSS vars, não em config do Tailwind).

---

## Checklist final (pré-merge)

- [ ] Todos os 17 commits do plano feitos.
- [ ] 10 páginas migradas com light + dark + mobile + desktop OK.
- [ ] Audit de duplicação limpo.
- [ ] README do DS escrito.
- [ ] Spec atualizado pra refletir o estado final.
- [ ] PR aberto descrevendo o escopo (link pro spec e pro plano).
