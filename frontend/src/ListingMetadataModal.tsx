import { type ReactNode, useEffect, useState } from "react";
import { ArrowDown, ArrowUp, ImagePlus, Plus, Trash2 } from "lucide-react";

import { catalogListings, type CommercialCatalogItem, type ListingImage, type ListingMetadataPayload } from "./api";
import { Button, Modal } from "./ui";

const emptyForm = (): ListingMetadataPayload => ({ online_sellable: false, listing_title: "", listing_description: "", condition: "", grade: "", public_price: 0, weight_per_unit: 0, package_length_cm: 0, package_width_cm: 0, package_height_cm: 0, images: [] });

export function ListingMetadataModal({ item, onClose, onSaved, open }: { item: CommercialCatalogItem | null; onClose: () => void; onSaved: (item: CommercialCatalogItem) => void; open: boolean }) {
  const [form, setForm] = useState<ListingMetadataPayload>(emptyForm());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!open || !item) return;
    setForm({ online_sellable: item.online_sellable, listing_title: item.listing_title, listing_description: item.listing_description, condition: item.condition, grade: item.grade, public_price: item.public_price, weight_per_unit: item.weight_per_unit, package_length_cm: item.package_length_cm, package_width_cm: item.package_width_cm, package_height_cm: item.package_height_cm, images: item.images });
    setMessage("");
  }, [item, open]);

  const update = <K extends keyof ListingMetadataPayload>(key: K, value: ListingMetadataPayload[K]) => setForm((current) => ({ ...current, [key]: value }));
  const updateImage = (index: number, key: keyof ListingImage, value: string) => update("images", form.images.map((image, current) => current === index ? { ...image, [key]: value } : image));
  const moveImage = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= form.images.length) return;
    const images = [...form.images];
    [images[index], images[target]] = [images[target], images[index]];
    update("images", images);
  };
  const save = async () => {
    if (!item) return;
    setBusy(true); setMessage("");
    try { onSaved((await catalogListings.save(item.item_code, form)).item); onClose(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível salvar os dados do anúncio."); }
    finally { setBusy(false); }
  };

  return <Modal className="max-w-4xl" onClose={onClose} open={open} title="Dados de anúncio">
    {item ? <div className="space-y-5">
      <div className="rounded-control border border-tec-border/20 bg-tec-field/50 p-3 text-sm text-tec-subtle"><strong className="text-white">{item.item_name}</strong><br />{item.catalog_kind === "unique" ? `Item único controlado por IMEI • final ${item.serial_suffix ?? "----"}` : `Variação da prateleira • pai ${item.variant_of}`}</div>
      <label className="flex items-center gap-3 rounded-control border border-tec-border/20 bg-tec-field/35 p-3 text-sm font-semibold text-white"><input checked={form.online_sellable} onChange={(event) => update("online_sellable", event.target.checked)} type="checkbox" /> Vendável online</label>
      <div className="grid gap-3 sm:grid-cols-2"><Field label="Título de anúncio"><input className="tp-input" onChange={(event) => update("listing_title", event.target.value)} value={form.listing_title} /></Field><Field label="Preço público"><input className="tp-input" inputMode="decimal" onChange={(event) => update("public_price", Number(event.target.value))} type="number" value={form.public_price || ""} /></Field></div>
      <Field label="Descrição de anúncio"><textarea className="tp-input min-h-24" onChange={(event) => update("listing_description", event.target.value)} value={form.listing_description} /></Field>
      <div className="grid gap-3 sm:grid-cols-4"><Field label="Condição"><select className="tp-input" onChange={(event) => update("condition", event.target.value)} value={form.condition}><option value="">Selecione</option><option>Novo</option><option>Usado</option></select></Field><Field label="Grade"><select className="tp-input" onChange={(event) => update("grade", event.target.value)} value={form.grade}><option value="">Não definida</option><option>A</option><option>B</option><option>C</option></select></Field><Field label="Peso (kg)"><input className="tp-input" inputMode="decimal" onChange={(event) => update("weight_per_unit", Number(event.target.value))} type="number" value={form.weight_per_unit || ""} /></Field><Field label="Comprimento (cm)"><input className="tp-input" inputMode="decimal" onChange={(event) => update("package_length_cm", Number(event.target.value))} type="number" value={form.package_length_cm || ""} /></Field></div>
      <div className="grid gap-3 sm:grid-cols-2"><Field label="Largura (cm)"><input className="tp-input" inputMode="decimal" onChange={(event) => update("package_width_cm", Number(event.target.value))} type="number" value={form.package_width_cm || ""} /></Field><Field label="Altura (cm)"><input className="tp-input" inputMode="decimal" onChange={(event) => update("package_height_cm", Number(event.target.value))} type="number" value={form.package_height_cm || ""} /></Field></div>
      <section className="space-y-3"><div className="flex items-center justify-between gap-3"><div><h3 className="font-bold text-white">Fotos do anúncio</h3><p className="text-sm text-tec-subtle">A primeira foto é a capa. Use caminhos de imagens já anexadas ao Item.</p></div><Button icon={<Plus size={16} />} onClick={() => update("images", [...form.images, { image: "", caption: "" }])}>Adicionar foto</Button></div>{form.images.map((image, index) => <div className="grid gap-2 rounded-control border border-tec-border/20 bg-tec-field/35 p-3 sm:grid-cols-[1fr_180px_auto]" key={`${image.image}-${index}`}><input aria-label={`Foto ${index + 1}`} className="tp-input" onChange={(event) => updateImage(index, "image", event.target.value)} placeholder="/files/foto-do-anuncio.jpg" value={image.image} /><input aria-label={`Legenda ${index + 1}`} className="tp-input" onChange={(event) => updateImage(index, "caption", event.target.value)} placeholder="Legenda" value={image.caption} /><div className="flex gap-1"><Button icon={<ArrowUp size={15} />} onClick={() => moveImage(index, -1)} title="Mover para cima" /><Button icon={<ArrowDown size={15} />} onClick={() => moveImage(index, 1)} title="Mover para baixo" /><Button icon={<Trash2 size={15} />} onClick={() => update("images", form.images.filter((_, current) => current !== index))} title="Remover foto" /></div></div>)}</section>
      {message ? <p className="rounded-control border border-tec-danger/35 bg-tec-danger/10 p-3 text-sm text-tec-danger">{message}</p> : null}
      <div className="flex justify-end gap-2"><Button onClick={onClose} variant="secondary">Cancelar</Button><Button disabled={busy} icon={<ImagePlus size={16} />} onClick={() => void save()} variant="primary">{busy ? "Salvando..." : "Salvar anúncio"}</Button></div>
    </div> : null}
  </Modal>;
}

function Field({ children, label }: { children: ReactNode; label: string }) { return <label className="block text-sm font-bold text-tec-text">{label}{children}</label>; }
