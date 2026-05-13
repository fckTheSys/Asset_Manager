CentiLeo Node Space — почему создаётся обычный материал вместо CentiLeo?

GetActiveNodeSpaceId() возвращает node space активного рендера. Если в Render
Settings выбран Standard или Physical — CreateDefaultGraph создаст обычный
граф (Standard Material), а не CentiLeo.

Что сделать:
1. Откройте Render Settings (Edit → Project Settings → Render Settings или Ctrl+B).
2. В поле Renderer выберите CentiLeo (не Standard, не Physical).
3. Соберите материалы с включённым чекбоксом CentiLeo.

Логи в консоли (Script Manager → Console):
   [TankToolBox][CL] Active node space: ...
Если видите "ERROR: Graph is not CentiLeo (active space=...)" — значит активный
рендер всё ещё Standard/Physical, выберите CentiLeo в Render Settings.
