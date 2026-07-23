# Procedimento de Limpeza de Massa de Teste

Este procedimento deve ser usado antes do go-live e sempre que o banco de desenvolvimento acumular muitos dados transacionais de teste.

## Objetivo

Reduzir OS, vendas, trocas, notificações, solicitações e anexos de teste sem afetar cadastros estruturais nem evidências jurídicas válidas.

## Antes de limpar

1. Gerar backup completo do banco e dos arquivos do site.
2. Copiar o backup para fora do WSL/Docker, em pasta do Windows, Drive ou storage externo.
3. Conferir hash dos arquivos copiados.
4. Rodar dry-run e listar quantos registros serão removidos por DocType.
5. Confirmar que os registros preservados continuam consistentes entre si.

## Preservar sempre

- Usuários, papéis e permissões.
- Tecponto Settings.
- SLAs por etapa.
- Catálogo de serviços, categorias e mapeamento defeito -> serviço.
- Categorias de produto, atributos, variações e produtos base.
- POS Profile, warehouses, contas, workflows e fixtures estruturais.
- Alguns exemplos transacionais mínimos para validação visual: OS em estados variados, uma venda, uma troca e uma solicitação pendente.

## Limpar massa transacional

Remover apenas dados de teste que não serão preservados, respeitando vínculos:

- Service Order e filhos.
- Sales Invoice, Payment Entry e Stock Entry de teste.
- Device Trade Evaluation / Trade-In Operation de teste.
- Tecponto Request.
- Tecponto Notification.
- Tecponto Part Request.
- OS Acceptance de teste.
- Service Order Tracking ligado a OS removida.
- File ligado a documentos removidos ou apontando para arquivo físico inexistente.

## Órfãos obrigatórios no plano

O plano de limpeza deve incluir explicitamente:

1. **Service Order Tracking órfão:** links de rastreio apontando para OS inexistente.
2. **File sem arquivo físico:** registros `File` cujo `file_url` aponta para `/files/` ou `/private/files/`, mas o arquivo não existe no disco.

Use as funções de apoio:

```text
tecponto_app.tecponto.cleanup.scan_orphans
tecponto_app.tecponto.cleanup.cleanup_orphan_tracking_links
tecponto_app.tecponto.cleanup.cleanup_missing_public_file_records
```

Fluxo recomendado:

```text
bench --site tecponto.localhost console
```

```python
from tecponto_app.tecponto.acceptance import audit_completed_acceptance_evidence
from tecponto_app.tecponto.cleanup import (
    scan_orphans,
    cleanup_orphan_tracking_links,
    cleanup_missing_public_file_records,
)

scan_orphans()
audit_completed_acceptance_evidence()
cleanup_orphan_tracking_links(dry_run=True)
cleanup_missing_public_file_records(dry_run=True)
```

Só executar a limpeza quando:

- `missing_private_file_records.count == 0`.
- `audit_completed_acceptance_evidence()` retornar `issues: []`.
- O dry-run confirmar que os `File` faltantes são públicos e não são selfie/assinatura de aceite.

Execução:

```python
cleanup_orphan_tracking_links(dry_run=False)
cleanup_missing_public_file_records(dry_run=False)
scan_orphans()
audit_completed_acceptance_evidence()
```

## Regra para evidências de aceite

Selfie e assinatura são prova jurídica. Nunca remover evidência privada automaticamente.

Se a auditoria apontar selfie/assinatura ausente, a limpeza deve parar em falha fechada. O caso precisa de análise manual antes de qualquer exclusão.

## Depois de limpar

1. Rodar `bench --site tecponto.localhost migrate`.
2. Rodar a suíte completa/foundation checks.
3. Rodar guards de dados sensíveis e custo por valor.
4. Rodar build/typecheck do front.
5. Registrar números finais: OS, vendas, clientes, aparelhos, aceites, tracking links, files órfãos e evidências válidas.

