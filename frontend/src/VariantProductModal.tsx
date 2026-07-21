import { useEffect, useMemo, useState } from "react";
import { Boxes, Plus, Tags } from "lucide-react";

import { pos, productVariants, type ProductVariantAttribute, type ProductVariantCreatePayload } from "./api";
import { Button, Modal } from "./ui";

interface VariantDraft {
  attributes: Record<string, string>;
  gtin: string;
  price: string;
  sku: string;
}

const DEFAULT_ATTRIBUTES = ["Cor", "Modelo compatível"];

export function VariantProductModal({ onClose, onCreated, open }: { onClose: () => void; onCreated: (message: string) => void; open: boolean }) {
  const [attributes, setAttributes] = useState<ProductVariantAttribute[]>([]);
  const [groups, setGroups] = useState<string[]>([]);
  const [selectedAttributes, setSelectedAttributes] = useState(DEFAULT_ATTRIBUTES);
  const [selectedValues, setSelectedValues] = useState<Record<string, string[]>>({});
  const [templateCode, setTemplateCode] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [itemGroup, setItemGroup] = useState("");
  const [variants, setVariants] = useState<VariantDraft[]>([]);
  const [newValues, setNewValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!open) return;
    setBusy(true);
    Promise.all([productVariants.listAttributes(), pos.listRetailItemGroups()])
      .then(([attributeResponse, groupResponse]) => {
        setAttributes(attributeResponse.items.filter((item) => !item.disabled));
        const nextGroups = groupResponse.items.map((item) => item.name);
        setGroups(nextGroups);
        setItemGroup((current) => current || nextGroups[0] || "Capas");
      })
      .catch(() => setMessage("Não foi possível carregar os atributos e categorias."))
      .finally(() => setBusy(false));
  }, [open]);

  const activeAttributes = useMemo(
    () => attributes.filter((attribute) => selectedAttributes.includes(attribute.name)),
    [attributes, selectedAttributes],
  );

  const toggleAttribute = (name: string) => {
    setSelectedAttributes((current) => current.includes(name) ? current.filter((item) => item !== name) : [...current, name]);
    setVariants([]);
  };

  const toggleValue = (attribute: string, value: string) => {
    setSelectedValues((current) => {
      const values = current[attribute] ?? [];
      return { ...current, [attribute]: values.includes(value) ? values.filter((item) => item !== value) : [...values, value] };
    });
    setVariants([]);
  };

  const generateCombinations = () => {
    if (!templateCode.trim() || !templateName.trim() || !activeAttributes.length) {
      setMessage("Informe o código, nome e ao menos um atributo antes de gerar as variações.");
      return;
    }
    const choices = activeAttributes.map((attribute) => ({ name: attribute.name, values: selectedValues[attribute.name] ?? [] }));
    if (choices.some((item) => !item.values.length)) {
      setMessage("Selecione pelo menos um valor para cada atributo escolhido.");
      return;
    }
    const combinations = cartesian(choices);
    if (combinations.length > 32) {
      setMessage("Limite operacional: selecione até 32 combinações por vez.");
      return;
    }
    setVariants(combinations.map((combination) => ({
      attributes: combination,
      gtin: "",
      price: "",
      sku: `${templateCode.trim()}-${Object.values(combination).map(compact).join("-")}`.toUpperCase(),
    })));
    setMessage(`${combinations.length} variação(ões) gerada(s). Complete SKU, GTIN/EAN e preço.`);
  };

  const updateVariant = (index: number, field: keyof VariantDraft, value: string) => {
    setVariants((current) => current.map((variant, currentIndex) => currentIndex === index ? { ...variant, [field]: value } : variant));
  };

  const addAttributeValue = async (attribute: string) => {
    const value = (newValues[attribute] ?? "").trim();
    if (!value) return;
    setBusy(true);
    try {
      const response = await productVariants.saveAttribute(attribute, [{ value }]);
      setAttributes((current) => current.map((item) => item.name === attribute ? response.item : item));
      setNewValues((current) => ({ ...current, [attribute]: "" }));
      setMessage(`Valor “${value}” adicionado a ${attribute}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível adicionar o valor do atributo.");
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (!variants.length) {
      setMessage("Gere as combinações antes de cadastrar.");
      return;
    }
    setBusy(true);
    try {
      const payload: ProductVariantCreatePayload = {
        attributes: activeAttributes.map((item) => ({ name: item.name })),
        item_group: itemGroup,
        stock_uom: "Nos",
        template_code: templateCode.trim(),
        template_name: templateName.trim(),
        variants: variants.map((variant) => ({
          attributes: variant.attributes,
          gtin: variant.gtin.trim(),
          price: Number(variant.price.replace(",", ".") || 0),
          sku: variant.sku.trim(),
        })),
      };
      const response = await productVariants.create(payload);
      onCreated(`${response.template.item_name} cadastrado com ${response.variants.length} variação(ões).`);
      onClose();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível cadastrar o produto com variações.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal className="max-w-6xl" onClose={onClose} open={open} title="Produto com variações">
      <div className="space-y-5">
        <div className="flex gap-3 rounded-control border border-tec-border/20 bg-tec-field/55 p-3 text-sm text-tec-subtle">
          <Boxes className="shrink-0 text-tec-orange" size={20} />
          <p>O produto pai não entra no estoque nem no PDV. Cada variação recebe SKU, GTIN/EAN, preço e saldo próprios.</p>
        </div>
        {message ? <p className="rounded-control border border-tec-orange/25 bg-tec-orange/10 px-3 py-2 text-sm text-tec-text">{message}</p> : null}

        <section className="grid gap-3 md:grid-cols-3">
          <label className="text-sm font-semibold text-white">Código do produto pai<input className="tp-input mt-1 w-full" onChange={(event) => { setTemplateCode(event.target.value); setVariants([]); }} placeholder="CAP-SILICONE" value={templateCode} /></label>
          <label className="text-sm font-semibold text-white">Nome interno<input className="tp-input mt-1 w-full" onChange={(event) => { setTemplateName(event.target.value); setVariants([]); }} placeholder="Capa silicone antichoque" value={templateName} /></label>
          <label className="text-sm font-semibold text-white">Categoria<select className="tp-input mt-1 w-full" onChange={(event) => setItemGroup(event.target.value)} value={itemGroup}>{groups.map((group) => <option key={group} value={group}>{group}</option>)}</select></label>
        </section>

        <section className="rounded-card border border-tec-border/15 bg-tec-field/25 p-4">
          <div className="flex items-center gap-2"><Tags className="text-tec-orange" size={18} /><h3 className="font-display text-lg font-bold text-white">Atributos e valores</h3></div>
          <p className="mt-1 text-sm text-tec-subtle">Selecione os atributos que formam a grade. Novos valores ficam disponíveis para os próximos produtos sem alterar variações existentes.</p>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {attributes.map((attribute) => {
              const selected = selectedAttributes.includes(attribute.name);
              return <div className="rounded-control border border-tec-border/15 bg-tec-panel/60 p-3" key={attribute.name}>
                <label className="flex items-center gap-2 font-semibold text-white"><input checked={selected} onChange={() => toggleAttribute(attribute.name)} type="checkbox" /> {attribute.name}</label>
                {selected ? <>
                  <div className="mt-3 flex flex-wrap gap-2">{attribute.values.map((value) => <label className={`cursor-pointer rounded-control border px-2.5 py-1.5 text-xs font-semibold ${selectedValues[attribute.name]?.includes(value.value) ? "border-tec-orange bg-tec-orange/15 text-tec-text" : "border-tec-border/20 text-tec-subtle"}`} key={value.value}><input checked={selectedValues[attribute.name]?.includes(value.value) ?? false} className="sr-only" onChange={() => toggleValue(attribute.name, value.value)} type="checkbox" />{value.value}</label>)}</div>
                  <div className="mt-3 flex gap-2"><input className="tp-input min-w-0 flex-1" onChange={(event) => setNewValues((current) => ({ ...current, [attribute.name]: event.target.value }))} placeholder="Novo valor" value={newValues[attribute.name] ?? ""} /><Button disabled={busy} icon={<Plus size={15} />} onClick={() => void addAttributeValue(attribute.name)}>Adicionar</Button></div>
                </> : null}
              </div>;
            })}
          </div>
          <div className="mt-4 flex justify-end"><Button disabled={busy} icon={<Boxes size={16} />} onClick={generateCombinations} variant="primary">Gerar combinações</Button></div>
        </section>

        {variants.length ? <section className="overflow-x-auto rounded-card border border-tec-border/15"><table className="min-w-[900px] w-full text-sm"><thead className="border-b border-tec-border/15 text-left text-xs font-bold uppercase tracking-wide text-tec-muted"><tr><th className="px-3 py-3">Variação</th><th className="px-3 py-3">SKU</th><th className="px-3 py-3">GTIN / EAN</th><th className="px-3 py-3">Preço de venda</th></tr></thead><tbody>{variants.map((variant, index) => <tr className="border-b border-tec-border/10" key={Object.values(variant.attributes).join("-")}><td className="px-3 py-2 text-tec-text">{Object.entries(variant.attributes).map(([key, value]) => <span className="mr-2" key={key}><span className="text-tec-muted">{key}:</span> {value}</span>)}</td><td className="px-3 py-2"><input className="tp-input w-full font-mono" onChange={(event) => updateVariant(index, "sku", event.target.value.toUpperCase())} value={variant.sku} /></td><td className="px-3 py-2"><input className="tp-input w-full font-mono" onChange={(event) => updateVariant(index, "gtin", event.target.value.replace(/\s+/g, ""))} placeholder="Código da embalagem" value={variant.gtin} /></td><td className="px-3 py-2"><input className="tp-input w-36" inputMode="decimal" min="0" onChange={(event) => updateVariant(index, "price", event.target.value)} placeholder="0,00" type="number" value={variant.price} /></td></tr>)}</tbody></table><p className="px-3 py-3 text-xs text-tec-muted">O estoque é lançado por variação na entrada comercial; o PDV baixa exclusivamente a variação bipada.</p></section> : null}
        <footer className="flex justify-end gap-2 border-t border-tec-border/15 pt-4"><Button onClick={onClose} variant="secondary">Cancelar</Button><Button disabled={busy || !variants.length} onClick={() => void save()} variant="primary">Cadastrar variações</Button></footer>
      </div>
    </Modal>
  );
}

function cartesian(attributes: Array<{ name: string; values: string[] }>) {
  return attributes.reduce<Array<Record<string, string>>>((rows, attribute) => rows.flatMap((row) => attribute.values.map((value) => ({ ...row, [attribute.name]: value }))), [{}]);
}

function compact(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^A-Za-z0-9]+/g, "").slice(0, 12);
}
