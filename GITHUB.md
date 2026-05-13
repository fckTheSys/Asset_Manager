# Публикация репозитория на GitHub

Рекомендуемое **имя репозитория**: `Asset_Manager`  
**Краткое описание (About)**:

> Cinema 4D pipeline: FBX + textures → Redshift/CentiLeo materials, relink, Camera Shake, utilities.

**Топики (Topics)** для GitHub: `cinema-4d`, `python`, `redshift`, `centileo`, `materials`, `fbx`, `pipeline`

## Вариант A: веб + git

1. GitHub → **New repository** → имя `Asset_Manager` → без конфликтующих README при первом push (или потом merge).
2. Локально:

```powershell
cd путь\к\Asset_Manager
git init
git add .
git commit -m "Initial commit: Tank Tool Box (Asset Manager) v2.1.0"
git branch -M main
git remote add origin https://github.com/YOUR_USER/Asset_Manager.git
git push -u origin main
```

## Вариант B: GitHub CLI

```powershell
cd путь\к\Asset_Manager
git init
git add .
git commit -m "Initial commit: Tank Tool Box v2.1.0"
gh repo create Asset_Manager --public --source=. --remote=origin --push
```

## Релизы

```powershell
git tag -a v2.1.0 -m "Tank Tool Box 2.1.0"
git push origin v2.1.0
```

Пользователям удобно выкладывать ZIP папки плагина как артефакт **Release**.
