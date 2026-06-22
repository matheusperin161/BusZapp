# BuszApp · Design System Unificado — Spec

**Data:** 2026-06-22
**Autor:** Guilherme Avila + Claude (brainstorming)
**Status:** Em revisão

---

## 1. Contexto e problema

O BuszApp tem hoje 16 páginas HTML em `static/`, cobrindo quatro perfis (público/auth, passageiro, motorista, admin). Há um `static/css/main.css` com pretensão de "design system" (tokens CSS, sidebar, animações), mas ele está **subutilizado**:

- Cada página redefine no `<style>` inline as mesmas peças: `form-input`, `modal-overlay`, `modal-box`, `btn-icon`, `badge`, `stat-card`, `section-panel`, `item-row` — com pequenas variações entre páginas.
- O header é inconsistente: `dashboard.html`, `add-driver.html`, `admin-rotas.html` usam o `header.js` compartilhado; `admin.html` tem o próprio header sem sidebar; `motorista.html`, `login.html` e `index.html` têm visuais próprios.
- A sidebar só existe em algumas páginas. Pages como `admin.html` e `motorista.html` não têm navegação lateral.
- `motorista.html` define um conjunto próprio de variáveis CSS (`--bg`, `--accent`) diferente do `main.css` principal.
- Dark mode está parcialmente implementado, com qualidade desigual entre páginas.

Resultado: visualmente o produto parece quatro produtos diferentes coexistindo, o trabalho de manter consistência é manual e propenso a erros, e mudanças visuais precisam ser repetidas em 10+ arquivos.

## 2. Objetivos

1. **Unificar a aparência** de todas as páginas autenticadas sob uma única identidade visual.
2. **Centralizar** os componentes reutilizáveis (botões, cards, modais, inputs, badges, tabs) em `main.css`, eliminando `<style>` duplicados nas páginas.
3. **Padronizar a navegação** com sidebar fixa no desktop e bottom nav no mobile.
4. **Manter dark mode** como cidadão de primeira classe — todo token tem par light/dark.
5. **Não alterar a arquitetura do projeto** (Python + Tailwind CDN + JS vanilla). Não introduzir build step.

## 3. Não-objetivos (v1)

- Não migrar páginas públicas/auth: `index.html`, `login.html`, `register.html`, `forgot-password.html`, `terms.html`. Essas ficam para uma fase 2.
- Não trocar Tailwind CDN por build local. Não introduzir Node/build step.
- Não criar Web Components ou framework JS. JS continua vanilla com helpers pontuais.
- Não redesenhar fluxos de negócio. Apenas padronizar a camada visual.
- Não reescrever a lógica do `header.js` atual além do necessário para acomodar a nova estrutura.

## 4. Decisões do brainstorming

| Decisão | Escolha |
|---|---|
| Estilo geral | Novo estilo unificado, amigável e colorido (mantendo amarelo/laranja como marca) |
| Paleta | **Sunset refinado** — amarelo/laranja vivos + neutros quentes (`#fffbeb`, `#fef3c7`) |
| Navegação | Bottom nav no mobile + sidebar fixa no desktop |
| Escopo de páginas | Apenas autenticadas (10 páginas). Auth/landing depois |
| Dark mode | Mantido e padronizado em todas as páginas |
| Rollout | Big bang — todas as páginas migram no mesmo release |
| Abordagem técnica | Tokens CSS + classes de componentes em `main.css` + helpers JS pontuais |
| Header desktop | Branco com sidebar gradiente (não gradiente nos dois) |
| Bottom nav | 5 itens fixos sem FAB central |

## 5. Arquitetura do design system

### 5.1 Organização de arquivos

```
static/
├── css/
│   ├── main.css              ← tokens + classes de componentes (reescrito)
│   ├── notifications.css     ← mantido (dropdown de notificações já isolado)
│   └── README.md             ← novo — explica como usar o DS
├── js/
│   ├── app.js                ← mantido (lógica de app)
│   ├── header.js             ← refatorado (nova estrutura)
│   ├── sidebar.js            ← NOVO — sidebar desktop + drawer mobile
│   ├── bottom-nav.js         ← NOVO — bottom nav mobile
│   ├── modal.js              ← NOVO — abrir/fechar modal padronizado
│   ├── toast.js              ← NOVO — feedback de ações (substitui alert())
│   └── notifications.js      ← mantido
```

### 5.2 Princípios

1. **Tokens via CSS variables**, com pares light/dark via `:root` e `.dark`.
2. **Classes utilitárias do Tailwind ainda permitidas** para layout (`grid`, `flex`, `gap-*`, `mx-auto`, `px-*`). Para componentes (botão, card, badge, input, modal, tab), usar as classes do design system (`bz-btn`, `bz-card`, etc.).
3. **Nenhum `<style>` por página** com exceções justificadas (ex: estilos muito específicos de mapas Leaflet ou animações de hero não reutilizáveis). Toda nova regra reutilizável vai pro `main.css`.
4. **Naming convention:** prefixo `bz-` (BuszApp) para todas as classes de componentes. Tokens em `--color-*`, `--space-*`, `--radius-*`, `--shadow-*`, `--font-*`.

## 6. Tokens

### 6.1 Cores (light mode)

```css
:root {
  /* Marca */
  --color-primary:        #f59e0b;
  --color-primary-dark:   #d97706;
  --color-primary-light:  #fbbf24;
  --color-accent:         #f97316;
  --gradient-brand:       linear-gradient(135deg, #fbbf24, #f97316);
  --gradient-sidebar:     linear-gradient(180deg, #fbbf24 0%, #f59e0b 50%, #d97706 100%);

  /* Superfícies */
  --color-bg:             #fffbeb;   /* fundo de página */
  --color-surface:        #ffffff;   /* cards, modais */
  --color-surface-2:      #fef3c7;   /* surface alternativo (chips, item-row bg) */
  --color-border:         #fde68a;
  --color-border-strong:  #f59e0b;

  /* Texto */
  --color-text:           #1f2937;
  --color-text-muted:     #6b7280;
  --color-text-inverse:   #ffffff;

  /* Semânticas */
  --color-success:        #10b981;
  --color-success-bg:     #dcfce7;
  --color-success-fg:     #166534;
  --color-danger:         #ef4444;
  --color-danger-bg:      #fee2e2;
  --color-danger-fg:      #991b1b;
  --color-warning:        #f59e0b;
  --color-warning-bg:     #fef3c7;
  --color-warning-fg:     #92400e;
  --color-info:           #2563eb;
  --color-info-bg:        #dbeafe;
  --color-info-fg:        #1e3a8a;

  /* Sombras */
  --shadow-sm:  0 2px 6px  rgba(245,158,11,.08);
  --shadow-md:  0 2px 12px rgba(245,158,11,.10);
  --shadow-lg:  0 12px 30px rgba(245,158,11,.20);
  --shadow-xl:  0 25px 60px rgba(0,0,0,.25);
}
```

### 6.2 Cores (dark mode)

```css
.dark {
  --color-bg:             #0f172a;
  --color-surface:        #1e293b;
  --color-surface-2:      #334155;
  --color-border:         #334155;
  --color-border-strong:  #fbbf24;

  --color-text:           #f8fafc;
  --color-text-muted:     #94a3b8;

  --color-success-bg:     #14532d;
  --color-success-fg:     #86efac;
  --color-danger-bg:      #7f1d1d;
  --color-danger-fg:      #fca5a5;
  --color-warning-bg:     #78350f;
  --color-warning-fg:     #fde68a;
  --color-info-bg:        #1e3a8a;
  --color-info-fg:        #bfdbfe;

  --shadow-sm:  0 2px 6px  rgba(0,0,0,.30);
  --shadow-md:  0 2px 12px rgba(0,0,0,.35);
  --shadow-lg:  0 12px 30px rgba(0,0,0,.50);
}
```

### 6.3 Tipografia

- **Família:** Inter (já disponível via Tailwind/CDN). Sem fonte custom adicional.
- **Escala:**
  - `--font-xs: 11px` (uppercase labels)
  - `--font-sm: 13px` (textos auxiliares, badges)
  - `--font-base: 14px` (corpo)
  - `--font-md: 16px` (h3, títulos de cards)
  - `--font-lg: 20px` (h2)
  - `--font-xl: 26px` (h1)
- **Pesos:** 400 normal, 600 medium, 700 bold, 800 extrabold, 900 black.
- **Line-height:** 1.5 para corpo, 1.2 para títulos.

### 6.4 Espaçamento e raios

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  --radius-sm: 8px;
  --radius-md: 12px;   /* botões, inputs, tabs */
  --radius-lg: 16px;   /* cards */
  --radius-xl: 18px;   /* modais, balance card */
  --radius-pill: 999px;
}
```

### 6.5 Estrutura de layout

```css
:root {
  --sidebar-collapsed: 70px;
  --sidebar-expanded:  220px;
  --header-height:     56px;
  --bottom-nav-height: 60px;
  --breakpoint-md:     768px;
}
```

## 7. Componentes

### 7.1 Sidebar (desktop)

- Posição: `fixed` à esquerda, altura `100dvh`.
- Largura: `--sidebar-collapsed` (70px) por padrão; expande para `--sidebar-expanded` (220px) no hover ou quando tem `.expanded`.
- Background: `var(--gradient-sidebar)`.
- Conteúdo:
  - Header da sidebar: logo `B` quadrada branca + nome "BuszApp" (visível só quando expandida).
  - Lista de itens (`.bz-sidebar-item`): ícone Feather 18px + label. Estado `.active` com background `rgba(255,255,255,.22)`.
  - Footer: botão "Sair" sticky no fundo.
- **Mobile:** vira drawer (off-canvas) acionado pelo `.bz-menu-toggle` no header.
- Items renderizados condicionalmente por perfil (passageiro/motorista/admin) — controlado em JS, mas a marcação é a mesma.

### 7.2 Header

- Desktop: branco, altura 56px, `border-bottom: 1px solid var(--color-border)`.
- Mobile: gradiente `var(--gradient-brand)`, altura 48px, branco no texto.
- Conteúdo: título da página à esquerda (com botão hamburger só no mobile), ações à direita (notificações, tema, avatar/perfil).
- Implementação: refator do `header.js` atual, mantendo a API de `data-*` attributes.

### 7.3 Bottom nav (mobile only)

- Posição: `fixed` no rodapé, altura 60px, `border-top: 1px solid var(--color-border)`.
- Background: `var(--color-surface)`.
- 5 itens: ícone + label minúsculo. Item ativo: ícone com gradiente da marca, label colorida e bold.
- Padding bottom no `<main>` deve respeitar essa altura quando o bottom nav está visível.
- Renderizado por `bottom-nav.js`, items variam por perfil (mesma lógica do sidebar).

### 7.4 Botões — `.bz-btn`

Modificadores: `.bz-btn-primary`, `.bz-btn-secondary`, `.bz-btn-ghost`, `.bz-btn-success`, `.bz-btn-danger`, `.bz-btn-icon`, `.bz-btn-sm`.

- Padding base: 10px 18px (sm: 6px 12px; icon: 38×38).
- Radius: `--radius-md` (12px).
- Font: 14px, peso 700.
- Primary: `background: var(--gradient-brand); color: white; box-shadow: 0 4px 14px rgba(249,115,22,.32)`. Hover: `translateY(-1px)`.
- Secondary: `background: var(--color-surface); color: var(--color-warning-fg); border: 2px solid var(--color-border)`.
- Ghost: transparente, hover background `--color-surface-2`.

### 7.5 Inputs — `.bz-input`

- Padding: 12px 14px.
- Border: 2px solid `--color-border`, focus `--color-border-strong` + halo `0 0 0 3px rgba(245,158,11,.18)`.
- Background: `--color-bg` neutro, `--color-surface` no focus.
- Wrapper opcional `.bz-input-wrap` com ícone à esquerda (Feather 16px), padding-left do input: 40px.
- Label `.bz-label`: 12px, peso 700, cor `--color-text`, margin-bottom 6px.

### 7.6 Badges — `.bz-badge`

Modificadores: `.bz-badge-success`, `.bz-badge-danger`, `.bz-badge-warning`, `.bz-badge-info`, `.bz-badge-neutral`.

- Padding: 3px 10px.
- Radius: `--radius-pill`.
- Font: 11px, peso 800, uppercase letter-spacing.
- Opcional `<span class="dot">` interno para indicador visual.

### 7.7 Cards

Quatro variantes:

- **`.bz-card`** (básico): `background: var(--color-surface); border-radius: var(--radius-lg); padding: 18px; box-shadow: var(--shadow-md); border: 1px solid var(--color-surface-2)`.
- **`.bz-stat-card`**: flex row com ícone quadrado 44×44 (gradiente da marca, ícone branco) + bloco com `value` (22px peso 900) + `label` (11px uppercase).
- **`.bz-balance-card`**: gradiente da marca, color white, círculos decorativos absolutos via `::before`/`::after`. Para destaque de saldo, total etc.
- **`.bz-item`** (linha de lista): flex row, padding 12px 14px, avatar 36×36 com gradiente + título + subtítulo + ação à direita.

### 7.8 Tabs — `.bz-tabs` / `.bz-tab`

- Container `.bz-tabs`: flex com gap 6px e wrap.
- Item `.bz-tab`: padding 8px 16px, radius 10px, background `--color-surface`, border 2px solid `--color-surface-2`.
- `.bz-tab.active`: `background: var(--gradient-brand); color: white; border-color: transparent`.
- Substitui as classes ad-hoc `.admin-tab`, `.route-tab` de hoje.

### 7.9 Modal — `.bz-modal-overlay` / `.bz-modal-box`

- Overlay: `position: fixed; inset: 0; background: rgba(0,0,0,.55); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 9999`. Escondido por padrão (`.hidden`).
- Box: `background: var(--color-surface); border-radius: var(--radius-xl); padding: 22px; width: 90%; max-width: 500px; max-height: 90vh; overflow-y: auto; box-shadow: var(--shadow-xl); animation: slideUp .3s ease`.
- Estrutura interna: `.bz-modal-title` (16px/800) + `.bz-modal-desc` (13px muted) + corpo livre + `.bz-modal-actions` (flex justify-end gap-8).
- Helper JS `modal.js`: `Modal.open(id)`, `Modal.close(id)` — fecha no ESC, fecha no clique fora.

### 7.10 Toasts (novo)

Helper JS `toast.js` para feedback de ações (substituindo `alert()` espalhados no código).

- `Toast.success(message)`, `Toast.error(message)`, `Toast.info(message)`.
- Renderizado em `position: fixed; top: 80px; right: 16px` (mobile: top center).
- Auto-dismiss em 4s.
- Visual: card pequeno com ícone semântico + texto, mesmas cores das badges.

## 8. Páginas a migrar (v1)

| Página | Perfil | Sidebar items | Bottom nav items |
|---|---|---|---|
| `dashboard.html` | passageiro | Início, Acompanhar, Recarga, Histórico, Avaliar | Início, Mapa, Recarga, Histórico, Perfil |
| `acompanhamento.html` | passageiro | mesmo | mesmo |
| `recarga.html` | passageiro | mesmo | mesmo |
| `rating.html` | passageiro | mesmo | mesmo |
| `profile.html` | comum | varia por papel | varia por papel |
| `motorista.html` | motorista | Painel, Rota atual, Perfil | Painel, Rota, Perfil |
| `admin.html` | admin | Visão geral, Motoristas, Frota, Rotas | apenas mobile fallback |
| `admin-rotas.html` | admin | mesmo | mesmo |
| `add-driver.html` | admin | mesmo | mesmo |
| `add-vehicle.html` | admin | mesmo | mesmo |

Total: **10 páginas autenticadas**. Cada migração: remover `<style>` inline, trocar classes ad-hoc pelas do DS, garantir sidebar+header+bottom-nav.

## 9. Plano de migração

1. **Bloco 1 — Fundação:**
   - Reescrever `main.css` com todos os tokens e classes acima.
   - Criar `sidebar.js`, `bottom-nav.js`, `modal.js`, `toast.js`.
   - Refatorar `header.js` (mantendo API atual).
   - Documentar uso em `static/css/README.md`.

2. **Bloco 2 — Migração de páginas (big bang):**
   - Para cada uma das 10 páginas:
     - Substituir bloco `<style>` por uso das classes do DS.
     - Substituir markup do header/sidebar pelo novo padrão.
     - Adicionar bottom-nav onde aplicável.
     - Verificar dark mode visualmente.

3. **Bloco 3 — Validação:**
   - Rodar o servidor local e abrir as 10 páginas no light e no dark.
   - Verificar comportamento mobile (< 768px) e desktop.
   - Conferir que não sobrou `<style>` duplicado.

## 10. Critérios de aceitação

- [ ] `main.css` contém todos os tokens e classes documentadas neste spec.
- [ ] Cada uma das 10 páginas autenticadas usa o novo header, sidebar (desktop) e bottom nav (mobile).
- [ ] Nenhuma das 10 páginas tem mais de 10 linhas de `<style>` inline (apenas estilos verdadeiramente específicos da página, como mapas).
- [ ] Light e dark mode funcionam em todas as 10 páginas com paridade visual.
- [ ] Modais usam `.bz-modal-overlay` + `.bz-modal-box` + helper `modal.js`.
- [ ] Botões, badges, inputs, cards e tabs usam classes `.bz-*`.
- [ ] `alert()` em fluxos visíveis são substituídos por `Toast.*`.

## 11. Riscos e mitigações

- **Risco:** componentes específicos (mapas Leaflet, charts) podem precisar de overrides locais. **Mitigação:** permitir `<style>` por página apenas para isso, com comentário explicando.
- **Risco:** dark mode pode ter regressões em páginas que não exercitamos visualmente. **Mitigação:** checklist visual no bloco 3, sweep manual.
- **Risco:** PR fica enorme (big bang). **Mitigação:** entregar bloco 1 (fundação) em um commit, depois cada página em commits separados dentro do mesmo PR para revisar incrementalmente.
- **Risco:** quebrar fluxo de logout/notificações. **Mitigação:** manter API do `header.js` (data-attributes) e do `notifications.js` intactas.

## 12. Fora do escopo deste spec

- Migração de páginas auth/landing (`index`, `login`, `register`, `forgot-password`, `terms`).
- Mudança de stack (build local, Web Components, React).
- Redesign de fluxos ou novas funcionalidades.
- Acessibilidade (ARIA, contraste WCAG) — vai vir junto com a implementação, mas não é tema central desta spec.
