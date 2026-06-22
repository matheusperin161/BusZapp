# BuszApp · Design System

Guia rápido de uso. Para a especificação completa, ver `docs/superpowers/specs/2026-06-22-design-system-unificado-design.md`.

---

## Princípios

1. **Use classes `.bz-*`** para componentes (botão, card, badge, input, modal, etc.).
2. **Tailwind continua válido**, mas só para utilitários de layout (`grid`, `flex`, `gap-*`, `mx-auto`, `px-*`, etc.). Para visuais reutilizáveis, prefira as classes do DS.
3. **Não escreva blocos `<style>` nas páginas.** Exceções: estilos verdadeiramente únicos (mapas Leaflet, animações de hero não reutilizáveis). Sempre comente o porquê.
4. **Dark mode é primeira classe.** Cada componente do DS tem par light/dark via `.dark` no `<html>`.

---

## Tokens (CSS variables)

Use em vez de hardcoded hex. Definidos em `main.css` topo. Acesse com `var(--token)`.

### Cores
| Token | Light | Dark | Uso |
|---|---|---|---|
| `--color-primary` | `#f59e0b` | igual | Cor de marca principal |
| `--color-primary-dark` | `#d97706` | igual | Hover de elementos primários |
| `--color-primary-light` | `#fbbf24` | igual | Topo do gradiente |
| `--color-accent` | `#f97316` | igual | Acento laranja |
| `--gradient-brand` | linear yellow→orange | igual | Botões primários, balance card, items ativos |
| `--gradient-sidebar` | linear yellow→orange→amber-dark | igual | Background da sidebar |
| `--color-bg` | `#fffbeb` | `#0f172a` | Fundo da página |
| `--color-surface` | `#ffffff` | `#1e293b` | Cards, modais |
| `--color-surface-2` | `#fef3c7` | `#334155` | Surface alternativo (chips, item bg) |
| `--color-border` | `#fde68a` | `#334155` | Bordas neutras |
| `--color-border-strong` | `#f59e0b` | `#fbbf24` | Foco de input, hover de borda |
| `--color-text` | `#1f2937` | `#f8fafc` | Texto primário |
| `--color-text-muted` | `#6b7280` | `#94a3b8` | Texto secundário |
| `--color-success`, `--color-success-bg`, `--color-success-fg` | semântica | semântica | Badge/alert verde |
| `--color-danger`, `--color-danger-bg`, `--color-danger-fg` | semântica | semântica | Badge/alert vermelho |
| `--color-warning`, `--color-warning-bg`, `--color-warning-fg` | semântica | semântica | Badge/alert amarelo |
| `--color-info`, `--color-info-bg`, `--color-info-fg` | semântica | semântica | Badge/alert azul |

### Espaçamento, raios, sombras

- Espaçamento: `--space-1` (4px) … `--space-8` (32px).
- Raios: `--radius-sm` (8px), `--radius-md` (12px) `--radius-lg` (16px), `--radius-xl` (18px), `--radius-pill` (999px).
- Sombras: `--shadow-sm`, `--shadow-md`, `--shadow-lg`, `--shadow-xl`.

### Layout

- `--sidebar-collapsed` (70px) / `--sidebar-expanded` (220px)
- `--header-height` (56px)
- `--bottom-nav-height` (60px)
- `--transition-base` (300ms easing)

---

## Componentes

### Botões — `.bz-btn`

```html
<button class="bz-btn bz-btn-primary">Confirmar</button>
<button class="bz-btn bz-btn-secondary">Cancelar</button>
<button class="bz-btn bz-btn-ghost">Mais opções</button>
<button class="bz-btn bz-btn-success">Salvar</button>
<button class="bz-btn bz-btn-danger">Excluir</button>

<!-- Modificadores de tamanho/forma -->
<button class="bz-btn bz-btn-primary bz-btn-sm">Pequeno</button>
<button class="bz-btn bz-btn-secondary bz-btn-icon" aria-label="Configurações">
  <i data-feather="settings"></i>
</button>
```

### Inputs — `.bz-input`

```html
<label class="bz-label">E-mail</label>
<input class="bz-input" placeholder="seu@email.com"/>

<!-- Com ícone à esquerda -->
<div class="bz-input-wrap">
  <i data-feather="search" class="bz-input-icon"></i>
  <input class="bz-input" placeholder="Buscar…"/>
</div>
```

### Badges — `.bz-badge`

```html
<span class="bz-badge bz-badge-success"><span class="dot"></span>Ativo</span>
<span class="bz-badge bz-badge-warning">Pendente</span>
<span class="bz-badge bz-badge-danger">Bloqueado</span>
<span class="bz-badge bz-badge-info">Em rota</span>
<span class="bz-badge bz-badge-neutral">Inativo</span>
```

### Cards

```html
<!-- Card básico -->
<div class="bz-card">
  <h3 class="bz-card-title">Última recarga</h3>
  <p class="bz-card-sub">R$ 50,00 via Pix · ontem</p>
</div>

<!-- Stat card (ícone + número + label) -->
<div class="bz-card bz-stat-card">
  <div class="bz-stat-icon"><i data-feather="users"></i></div>
  <div>
    <div class="bz-stat-value">128</div>
    <div class="bz-stat-label">Motoristas</div>
  </div>
</div>

<!-- Balance card (gradiente da marca, branco no texto) -->
<div class="bz-balance-card">
  <div class="bz-balance-card-label">Saldo atual</div>
  <div class="bz-balance-card-value">R$ 45,80</div>
  <div class="bz-balance-card-sub">Atualizado há 2 min</div>
</div>

<!-- Item de lista -->
<div class="bz-item">
  <div class="bz-item-avatar">JS</div>
  <div class="bz-item-main">
    <div class="bz-item-title">João Silva</div>
    <div class="bz-item-sub">CNH B · Linha 042</div>
  </div>
  <span class="bz-badge bz-badge-success">Ativo</span>
</div>
```

### Tabs — `.bz-tabs` / `.bz-tab`

```html
<div class="bz-tabs">
  <button class="bz-tab active">Geral</button>
  <button class="bz-tab">Motoristas</button>
  <button class="bz-tab">Frota</button>
</div>
```

### Modal — `.bz-modal-overlay` + `.bz-modal-box`

```html
<div id="deleteModal" class="bz-modal-overlay hidden">
  <div class="bz-modal-box">
    <h3 class="bz-modal-title">Confirmar exclusão</h3>
    <p class="bz-modal-desc">Esta ação não pode ser desfeita.</p>
    <!-- conteúdo livre -->
    <div class="bz-modal-actions">
      <button class="bz-btn bz-btn-ghost" onclick="Modal.close('deleteModal')">Cancelar</button>
      <button class="bz-btn bz-btn-danger">Excluir</button>
    </div>
  </div>
</div>
```

Abrir/fechar via JS (carregue `js/modal.js`):
```js
Modal.open('deleteModal');
Modal.close('deleteModal');

// Confirm ad-hoc (não precisa declarar HTML)
Modal.confirm({
  title: 'Excluir motorista?',
  desc:  'Esta ação não pode ser desfeita.',
  confirmText: 'Excluir',
  confirmVariant: 'danger',
  onConfirm: () => deleteDriver(id),
});
```

### Toasts (já existem)

```js
Toast.success('Recarga realizada com sucesso!');
Toast.error('Cartão não aceito.');
Toast.warning('Saldo baixo.');
Toast.info('Ônibus chegando em 2 min.');
```

CSS já está em `main.css` — basta usar a API. Substitua `alert()` por estes.

---

## Navegação

A sidebar (desktop) e a bottom nav (mobile) são auto-injetadas pelos respectivos scripts. **Não escreva markup `<nav>` para navegação manualmente.**

```html
<!-- Inclua nestes pontos do <body>, depois do app.js -->
<script src="./js/sidebar.js"></script>
<script src="./js/bottom-nav.js"></script>
```

Os scripts detectam o papel do usuário via `/api/auth/profile` automaticamente. Se você sabe o papel de antemão (página exclusiva, ex: `motorista.html`), defina via data-attribute para evitar piscar:

```html
<script src="./js/sidebar.js"    data-role="motorista"></script>
<script src="./js/bottom-nav.js" data-role="motorista"></script>
```

Valores válidos: `passageiro`, `motorista`, `admin`.

---

## Header

```html
<script src="./js/header.js"
        data-title="Painel"
        data-subtitle-id="headerSub"
        data-subtitle="Olá, Guilherme"
        data-show-theme="true"
        data-show-notifications="true"
        data-show-profile="true"></script>
```

O header é branco no desktop e gradiente no mobile (CSS faz a transição automática).

---

## Boilerplate de página nova

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Minha Página – BuszApp</title>

  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config = { darkMode: 'class' }</script>
  <script src="https://cdn.jsdelivr.net/npm/feather-icons/dist/feather.min.js" defer></script>

  <link rel="shortcut icon" href="./img/icone.png" type="image/x-icon"/>
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#f59e0b">
  <link rel="apple-touch-icon" href="/static/img/icon-192x192.png">

  <link rel="stylesheet" href="./css/main.css"/>
  <link rel="stylesheet" href="./css/notifications.css"/>
</head>
<body>

  <script src="./js/header.js"
          data-title="Minha Página"
          data-show-theme="true"
          data-show-notifications="true"
          data-show-profile="true"></script>

  <main class="container mx-auto px-4 py-6 max-w-5xl">
    <div class="bz-card">
      <h2 class="bz-card-title">Conteúdo</h2>
      <p class="bz-card-sub">Use as classes do DS.</p>
    </div>
  </main>

  <script src="./js/app.js"></script>
  <script src="./js/sidebar.js"></script>
  <script src="./js/bottom-nav.js"></script>
  <script src="./js/modal.js"></script>
  <script src="./js/notifications.js"></script>
</body>
</html>
```

---

## Convenções

- **Naming:** classes de componente sempre `.bz-` prefixadas. Estados via classes (`active`, `hidden`, `open`, `visible`).
- **Dark mode:** já sai funcionando se você usar tokens. Não escreva `.dark .meu-component` manualmente — use `var(--color-*)`.
- **Acessibilidade:** todos os botões interativos devem ter `aria-label` quando não tiverem texto. Modais usam ESC para fechar (modal.js cuida).
- **Mobile:** o bottom nav ocupa 60px no rodapé. O CSS já adiciona padding-bottom no `<main>` quando ele está presente.
