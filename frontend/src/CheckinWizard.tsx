import {
  type HTMLInputAutoCompleteAttribute,
  type HTMLInputTypeAttribute,
  type PointerEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ArrowRight,
  Camera,
  CheckCircle2,
  PenLine,
  Printer,
  RotateCcw,
  Search,
  Smartphone,
  Upload,
  UserRound,
} from "lucide-react";

import {
  balcao,
  checkin,
  type CheckinPayload,
  type CheckinResponse,
  type CustomerDeviceSummary,
  type CustomerSummary,
} from "./api";
import { Button, Modal } from "./ui";

const steps = ["Cliente", "Aparelho", "Dados", "Fotos", "Assinatura"];
const isLocalhost = ["localhost", "127.0.0.1"].includes(window.location.hostname) || window.location.hostname.endsWith(".localhost");

type NewCustomerForm = {
  customer_name: string;
  mobile_no: string;
  custom_cpf: string;
  custom_rg: string;
  custom_nao_possui_cpf: boolean;
  email_id: string;
};

type NewDeviceForm = {
  brand: string;
  model: string;
  color: string;
  imei_serial: string;
  capacity: string;
  general_state: string;
};

interface CheckinWizardProps {
  open: boolean;
  onClose: () => void;
  onCreated: (response: CheckinResponse) => void;
  onOpenOrder: (name: string) => void;
}

export function CheckinWizard({ onClose, onCreated, onOpenOrder, open }: CheckinWizardProps) {
  const [step, setStep] = useState(0);
  const [created, setCreated] = useState<CheckinResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [customerQuery, setCustomerQuery] = useState("");
  const [customerRows, setCustomerRows] = useState<CustomerSummary[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerSummary | null>(null);
  const [newCustomer, setNewCustomer] = useState<NewCustomerForm>({
    customer_name: "",
    mobile_no: "",
    custom_cpf: "",
    custom_rg: "",
    custom_nao_possui_cpf: false,
    email_id: "",
  });

  const [deviceQuery, setDeviceQuery] = useState("");
  const [deviceRows, setDeviceRows] = useState<CustomerDeviceSummary[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<CustomerDeviceSummary | null>(null);
  const [newDevice, setNewDevice] = useState<NewDeviceForm>({
    brand: "",
    model: "",
    color: "",
    imei_serial: "",
    capacity: "",
    general_state: "",
  });

  const [serviceOrder, setServiceOrder] = useState({
    reported_defect: "",
    physical_state: "",
    accessories_received: "",
  });
  const [photo, setPhoto] = useState<{ dataUrl: string; filename: string } | null>(null);
  const [signature, setSignature] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    setStep(0);
    setCreated(null);
    setSubmitting(false);
    setError(null);
  }, [open]);

  const customerReady = Boolean(
    selectedCustomer ||
      (newCustomer.customer_name.trim() &&
        newCustomer.mobile_no.trim() &&
        (newCustomer.custom_cpf.trim() || (newCustomer.custom_nao_possui_cpf && newCustomer.custom_rg.trim()))),
  );
  const deviceReady = Boolean(
    selectedDevice
      ? selectedDevice.imei_serial
      : newDevice.brand.trim() && newDevice.model.trim() && newDevice.imei_serial.trim(),
  );
  const dataReady = Boolean(serviceOrder.reported_defect.trim() && serviceOrder.physical_state.trim());
  const photoReady = Boolean(photo?.dataUrl);
  const signatureReady = Boolean(signature);
  const canContinue = [customerReady, deviceReady, dataReady, photoReady, signatureReady][step] ?? false;

  const searchCustomers = useCallback(async () => {
    setError(null);
    const response = await balcao.searchCustomers(customerQuery, 8);
    setCustomerRows(response.items);
  }, [customerQuery]);

  const searchDevices = useCallback(async () => {
    setError(null);
    const response = await balcao.listDevices(deviceQuery, 8);
    const rows = selectedCustomer
      ? response.items.filter((device) => device.customer === selectedCustomer.name)
      : response.items;
    setDeviceRows(rows);
  }, [deviceQuery, selectedCustomer]);

  async function submit() {
    setError(null);
    if (!photo || !signature) {
      setError("Foto e assinatura de entrada são obrigatórias para o check-in.");
      return;
    }

    const payload: CheckinPayload = {
      customer: selectedCustomer
        ? { existing_name: selectedCustomer.name }
        : {
            customer_name: newCustomer.customer_name.trim(),
            mobile_no: newCustomer.mobile_no.trim(),
            custom_whatsapp: newCustomer.mobile_no.trim(),
            custom_cpf: newCustomer.custom_cpf.trim(),
            custom_rg: newCustomer.custom_rg.trim(),
            custom_nao_possui_cpf: newCustomer.custom_nao_possui_cpf,
            email_id: newCustomer.email_id.trim(),
          },
      device: selectedDevice
        ? { existing_name: selectedDevice.name }
        : {
            brand: newDevice.brand.trim(),
            model: newDevice.model.trim(),
            color: newDevice.color.trim(),
            imei_serial: newDevice.imei_serial.trim(),
            capacity: newDevice.capacity.trim(),
            general_state: newDevice.general_state.trim(),
          },
      service_order: {
        reported_defect: serviceOrder.reported_defect.trim(),
        physical_state: serviceOrder.physical_state.trim(),
        accessories_received: serviceOrder.accessories_received.trim(),
      },
      entry_photo: {
        data_url: photo.dataUrl,
        filename: photo.filename,
      },
      entry_signature: signature,
    };

    setSubmitting(true);
    try {
      const response = await checkin.createServiceOrder(payload);
      setCreated(response);
      onCreated(response);
      setStep(steps.length);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao criar a OS.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal className="max-w-5xl" onClose={onClose} open={open} title={created ? "OS criada" : "Nova OS / check-in"}>
      <div>
        {created ? (
          <CheckinSuccess created={created} onClose={onClose} onOpenOrder={onOpenOrder} />
        ) : (
          <>
            <StepHeader step={step} />
            <div className="mt-5 min-h-[430px]">
              {step === 0 ? (
                <CustomerStep
                  customerQuery={customerQuery}
                  customerRows={customerRows}
                  newCustomer={newCustomer}
                  onSearch={searchCustomers}
                  selectedCustomer={selectedCustomer}
                  setCustomerQuery={setCustomerQuery}
                  setNewCustomer={setNewCustomer}
                  setSelectedCustomer={setSelectedCustomer}
                />
              ) : null}
              {step === 1 ? (
                <DeviceStep
                  deviceQuery={deviceQuery}
                  deviceRows={deviceRows}
                  newDevice={newDevice}
                  onSearch={searchDevices}
                  selectedCustomer={selectedCustomer}
                  selectedDevice={selectedDevice}
                  setDeviceQuery={setDeviceQuery}
                  setNewDevice={setNewDevice}
                  setSelectedDevice={setSelectedDevice}
                />
              ) : null}
              {step === 2 ? <ServiceDataStep serviceOrder={serviceOrder} setServiceOrder={setServiceOrder} /> : null}
              {step === 3 ? <PhotoStep photo={photo} setPhoto={setPhoto} /> : null}
              {step === 4 ? <SignatureStep signature={signature} setSignature={setSignature} /> : null}
            </div>

            {error ? <div className="mt-4 rounded-card border border-tec-red/30 bg-tec-red/10 p-3 text-sm text-tec-red">{error}</div> : null}

            <div className="mt-5 flex flex-col gap-3 border-t border-tec-border/20 pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-tec-muted">
                Foto e assinatura ficam salvas na OS e serão exigidas pelo motor antes de qualquer avanço técnico.
              </p>
              <div className="flex gap-2">
                <Button disabled={step === 0 || submitting} onClick={() => setStep((current) => Math.max(0, current - 1))}>
                  Voltar
                </Button>
                {step < steps.length - 1 ? (
                  <Button disabled={!canContinue} icon={<ArrowRight size={17} />} onClick={() => setStep((current) => current + 1)} variant="primary">
                    Avançar
                  </Button>
                ) : (
                  <Button disabled={!canContinue || submitting} icon={<CheckCircle2 size={17} />} onClick={submit} variant="primary">
                    {submitting ? "Criando..." : "Criar OS"}
                  </Button>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}

function StepHeader({ step }: { step: number }) {
  return (
    <div className="grid gap-2 sm:grid-cols-5">
      {steps.map((label, index) => (
        <div
          className={`rounded-card border px-3 py-2 text-sm ${
            index === step
              ? "border-tec-orange bg-tec-orange/15 text-white"
              : index < step
                ? "border-tec-success/30 bg-tec-success/10 text-tec-success"
                : "border-tec-border/20 bg-tec-panel-strong text-tec-muted"
          }`}
          key={label}
        >
          <span className="block text-[10px] font-bold uppercase">Passo {index + 1}</span>
          <span className="font-semibold">{label}</span>
        </div>
      ))}
    </div>
  );
}

function CustomerStep({
  customerQuery,
  customerRows,
  newCustomer,
  onSearch,
  selectedCustomer,
  setCustomerQuery,
  setNewCustomer,
  setSelectedCustomer,
}: {
  customerQuery: string;
  customerRows: CustomerSummary[];
  newCustomer: NewCustomerForm;
  onSearch: () => void;
  selectedCustomer: CustomerSummary | null;
  setCustomerQuery: (value: string) => void;
  setNewCustomer: (value: NewCustomerForm) => void;
  setSelectedCustomer: (value: CustomerSummary | null) => void;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section>
        <SectionTitle icon={<Search size={18} />} title="Buscar cliente" />
        <div className="mt-3 flex gap-2">
          <input
            className="h-11 flex-1 rounded-control border border-tec-border/25 bg-tec-field px-4 text-sm text-white outline-none focus:border-tec-orange/70"
            onChange={(event) => setCustomerQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void onSearch();
              }
            }}
            placeholder="Nome, telefone, CPF ou RG"
            value={customerQuery}
          />
          <Button icon={<Search size={17} />} onClick={() => void onSearch()} variant="primary">
            Buscar
          </Button>
        </div>
        <div className="mt-3 space-y-2">
          {customerRows.map((customer) => (
            <button
              className={`w-full rounded-card border p-3 text-left text-sm transition ${
                selectedCustomer?.name === customer.name
                  ? "border-tec-orange bg-tec-orange/10"
                  : "border-tec-border/20 bg-tec-panel-strong hover:border-tec-orange/50"
              }`}
              key={customer.name}
              onClick={() => setSelectedCustomer(customer)}
              type="button"
            >
              <span className="block font-bold text-white">{customer.customer_name ?? customer.name}</span>
              <span className="mt-1 block text-xs text-tec-muted">
                {[customer.mobile_no, customer.custom_cpf || customer.custom_rg, customer.email_id].filter(Boolean).join(" · ") || customer.name}
              </span>
            </button>
          ))}
        </div>
      </section>
      <section>
        <SectionTitle icon={<UserRound size={18} />} title={selectedCustomer ? "Cliente selecionado" : "Criar cliente"} />
        {selectedCustomer ? (
          <SelectedBox
            lines={[
              selectedCustomer.customer_name ?? selectedCustomer.name,
              selectedCustomer.mobile_no ?? "Sem telefone",
              selectedCustomer.custom_cpf
                ? `CPF: ${selectedCustomer.custom_cpf}`
                : selectedCustomer.custom_rg
                  ? `RG: ${selectedCustomer.custom_rg}`
                  : "Sem documento",
              selectedCustomer.email_id ?? "Sem e-mail",
            ]}
            onClear={() => setSelectedCustomer(null)}
          />
        ) : (
          <div className="mt-3 space-y-3">
            <Field
              autoComplete="name"
              label="Nome"
              onChange={(value) => setNewCustomer({ ...newCustomer, customer_name: value })}
              required
              value={newCustomer.customer_name}
            />
            <Field
              autoComplete="tel"
              inputMode="tel"
              label="Telefone/WhatsApp"
              onChange={(value) => setNewCustomer({ ...newCustomer, mobile_no: value })}
              placeholder="(11) 99999-9999"
              required
              type="tel"
              value={newCustomer.mobile_no}
            />
            <button
              aria-pressed={newCustomer.custom_nao_possui_cpf}
              className={`min-h-10 rounded-control border px-3 text-left text-sm font-bold transition ${
                newCustomer.custom_nao_possui_cpf
                  ? "border-tec-orange bg-tec-orange text-tec-ink"
                  : "border-tec-border/25 bg-tec-field text-tec-subtle hover:border-tec-orange/50 hover:text-white"
              }`}
              onClick={() =>
                setNewCustomer({
                  ...newCustomer,
                  custom_cpf: "",
                  custom_nao_possui_cpf: !newCustomer.custom_nao_possui_cpf,
                })
              }
              type="button"
            >
              Cliente não possui CPF
            </button>
            {newCustomer.custom_nao_possui_cpf ? (
              <Field
                autoComplete="off"
                label="RG"
                onChange={(value) => setNewCustomer({ ...newCustomer, custom_rg: value })}
                placeholder="Documento RG"
                required
                value={newCustomer.custom_rg}
              />
            ) : (
              <Field
                autoComplete="off"
                inputMode="numeric"
                label="CPF"
                maxLength={14}
                onChange={(value) => setNewCustomer({ ...newCustomer, custom_cpf: value })}
                placeholder="000.000.000-00"
                required
                value={newCustomer.custom_cpf}
              />
            )}
            <Field
              autoComplete="email"
              inputMode="email"
              label="E-mail"
              onChange={(value) => setNewCustomer({ ...newCustomer, email_id: value })}
              placeholder="cliente@email.com"
              type="email"
              value={newCustomer.email_id}
            />
          </div>
        )}
      </section>
    </div>
  );
}

function DeviceStep({
  deviceQuery,
  deviceRows,
  newDevice,
  onSearch,
  selectedCustomer,
  selectedDevice,
  setDeviceQuery,
  setNewDevice,
  setSelectedDevice,
}: {
  deviceQuery: string;
  deviceRows: CustomerDeviceSummary[];
  newDevice: NewDeviceForm;
  onSearch: () => void;
  selectedCustomer: CustomerSummary | null;
  selectedDevice: CustomerDeviceSummary | null;
  setDeviceQuery: (value: string) => void;
  setNewDevice: (value: NewDeviceForm) => void;
  setSelectedDevice: (value: CustomerDeviceSummary | null) => void;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_420px]">
      <section>
        <SectionTitle icon={<Search size={18} />} title="Buscar aparelho" />
        <div className="mt-3 flex gap-2">
          <input
            className="h-11 flex-1 rounded-control border border-tec-border/25 bg-tec-field px-4 text-sm text-white outline-none focus:border-tec-orange/70"
            onChange={(event) => setDeviceQuery(event.target.value)}
            placeholder="Modelo, IMEI ou cadastro"
            value={deviceQuery}
          />
          <Button icon={<Search size={17} />} onClick={() => void onSearch()} variant="primary">
            Buscar
          </Button>
        </div>
        <p className="mt-2 text-xs text-tec-muted">
          {selectedCustomer ? "A busca mostra aparelhos deste cliente." : "Selecione um cliente existente para filtrar aparelhos já cadastrados."}
        </p>
        <div className="mt-3 space-y-2">
          {deviceRows.map((device) => (
            <button
              className={`w-full rounded-card border p-3 text-left text-sm transition ${
                selectedDevice?.name === device.name
                  ? "border-tec-orange bg-tec-orange/10"
                  : "border-tec-border/20 bg-tec-panel-strong hover:border-tec-orange/50"
              }`}
              key={device.name}
              onClick={() => setSelectedDevice(device)}
              type="button"
            >
              <span className="block font-bold text-white">{[device.brand, device.model, device.color].filter(Boolean).join(" ") || device.name}</span>
              <span className="mt-1 block text-xs text-tec-muted">{[device.imei_serial, device.capacity, device.name].filter(Boolean).join(" · ")}</span>
            </button>
          ))}
        </div>
      </section>
      <section>
        <SectionTitle icon={<Smartphone size={18} />} title={selectedDevice ? "Aparelho selecionado" : "Criar aparelho"} />
        {selectedDevice ? (
          <>
            <SelectedBox
              lines={[
                [selectedDevice.brand, selectedDevice.model, selectedDevice.color].filter(Boolean).join(" ") || selectedDevice.name,
                selectedDevice.imei_serial ?? "Sem IMEI",
                selectedDevice.capacity ?? "Sem capacidade",
              ]}
              onClear={() => setSelectedDevice(null)}
            />
            {!selectedDevice.imei_serial ? (
              <p className="mt-3 rounded-card border border-tec-red/30 bg-tec-red/10 p-3 text-sm text-tec-red">
                Este aparelho está sem IMEI/serial no cadastro e não pode abrir OS até ser corrigido.
              </p>
            ) : null}
          </>
        ) : (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Field label="Marca" onChange={(value) => setNewDevice({ ...newDevice, brand: value })} required value={newDevice.brand} />
            <Field label="Modelo" onChange={(value) => setNewDevice({ ...newDevice, model: value })} required value={newDevice.model} />
            <Field label="Cor" onChange={(value) => setNewDevice({ ...newDevice, color: value })} value={newDevice.color} />
            <Field label="Capacidade" onChange={(value) => setNewDevice({ ...newDevice, capacity: value })} value={newDevice.capacity} />
            <div className="sm:col-span-2">
              <Field
                autoComplete="off"
                inputMode="numeric"
                label="IMEI / Serial"
                maxLength={18}
                onChange={(value) => setNewDevice({ ...newDevice, imei_serial: value })}
                placeholder="15 dígitos do IMEI ou serial"
                required
                value={newDevice.imei_serial}
              />
            </div>
            <div className="sm:col-span-2">
              <TextArea label="Estado geral do aparelho" onChange={(value) => setNewDevice({ ...newDevice, general_state: value })} value={newDevice.general_state} />
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function ServiceDataStep({
  serviceOrder,
  setServiceOrder,
}: {
  serviceOrder: { reported_defect: string; physical_state: string; accessories_received: string };
  setServiceOrder: (value: { reported_defect: string; physical_state: string; accessories_received: string }) => void;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <TextArea label="Defeito relatado" onChange={(value) => setServiceOrder({ ...serviceOrder, reported_defect: value })} required value={serviceOrder.reported_defect} />
      <TextArea label="Estado físico declarado" onChange={(value) => setServiceOrder({ ...serviceOrder, physical_state: value })} required value={serviceOrder.physical_state} />
      <TextArea label="Acessórios recebidos" onChange={(value) => setServiceOrder({ ...serviceOrder, accessories_received: value })} value={serviceOrder.accessories_received} />
    </div>
  );
}

function PhotoStep({
  photo,
  setPhoto,
}: {
  photo: { dataUrl: string; filename: string } | null;
  setPhoto: (value: { dataUrl: string; filename: string } | null) => void;
}) {
  async function handleFile(file: File | undefined) {
    if (!file) {
      return;
    }
    const dataUrl = await readFileAsDataUrl(file);
    setPhoto({ dataUrl, filename: file.name });
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
      <section className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4">
        <SectionTitle icon={<Camera size={18} />} title="Foto de entrada" />
        <p className="mt-3 text-sm text-tec-subtle">
          A OS nasce com foto anexada. Sem foto, o motor bloqueia a saída de Entrada criada.
        </p>
        <label className="mt-5 flex min-h-[140px] cursor-pointer flex-col items-center justify-center rounded-card border border-dashed border-tec-border/35 bg-tec-panel-strong p-4 text-center transition hover:border-tec-orange/60">
          <Upload className="text-tec-orange" size={28} />
          <span className="mt-3 text-sm font-bold text-white">Selecionar foto / câmera</span>
          <span className="mt-1 text-xs text-tec-muted">JPG, PNG ou imagem capturada no aparelho</span>
          <input
            accept="image/*"
            capture="environment"
            className="sr-only"
            onChange={(event) => void handleFile(event.currentTarget.files?.[0])}
            type="file"
          />
        </label>
        {isLocalhost ? (
          <Button className="mt-3 w-full" onClick={() => setPhoto(makeLocalTestPhoto())} variant="secondary">
            Foto teste local
          </Button>
        ) : null}
      </section>
      <section className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4">
        <h3 className="text-sm font-bold text-white">Prévia</h3>
        {photo ? (
          <div className="mt-3">
            <img alt="Foto de entrada" className="max-h-[340px] w-full rounded-card object-cover" src={photo.dataUrl} />
            <p className="mt-2 text-xs text-tec-muted">{photo.filename}</p>
          </div>
        ) : (
          <div className="mt-3 grid min-h-[260px] place-items-center rounded-card border border-tec-border/20 text-sm text-tec-muted">
            Nenhuma foto anexada.
          </div>
        )}
      </section>
    </div>
  );
}

function SignatureStep({
  setSignature,
  signature,
}: {
  setSignature: (value: string | null) => void;
  signature: string | null;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawing = useRef(false);

  const resetCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.fillStyle = "#fff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.strokeStyle = "#111827";
    context.lineWidth = 3;
    context.lineCap = "round";
    context.lineJoin = "round";
    setSignature(null);
  }, [setSignature]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const ratio = window.devicePixelRatio || 1;
    canvas.width = 720 * ratio;
    canvas.height = 220 * ratio;
    canvas.style.width = "100%";
    canvas.style.height = "220px";
    const context = canvas.getContext("2d");
    if (context) {
      context.scale(ratio, ratio);
    }
    resetCanvas();
  }, [resetCanvas]);

  function point(event: PointerEvent<HTMLCanvasElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    };
  }

  function begin(event: PointerEvent<HTMLCanvasElement>) {
    const context = canvasRef.current?.getContext("2d");
    if (!context) {
      return;
    }
    const current = point(event);
    drawing.current = true;
    context.beginPath();
    context.moveTo(current.x, current.y);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function move(event: PointerEvent<HTMLCanvasElement>) {
    if (!drawing.current) {
      return;
    }
    const context = canvasRef.current?.getContext("2d");
    if (!context) {
      return;
    }
    const current = point(event);
    context.lineTo(current.x, current.y);
    context.stroke();
  }

  function end(event: PointerEvent<HTMLCanvasElement>) {
    if (!drawing.current) {
      return;
    }
    drawing.current = false;
    event.currentTarget.releasePointerCapture(event.pointerId);
    setSignature(canvasRef.current?.toDataURL("image/png") ?? null);
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
      <section>
        <SectionTitle icon={<PenLine size={18} />} title="Assinatura de entrada" />
        <p className="mt-3 text-sm text-tec-subtle">
          O cliente assina confirmando o estado declarado do aparelho. Sem assinatura, o motor bloqueia o avanço técnico.
        </p>
        <canvas
          className="mt-4 touch-none rounded-card border border-tec-border/30 bg-white"
          onPointerCancel={end}
          onPointerDown={begin}
          onPointerMove={move}
          onPointerUp={end}
          ref={canvasRef}
        />
      </section>
      <aside className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4">
        <h3 className="text-sm font-bold text-white">Status</h3>
        <p className={`mt-3 text-sm ${signature ? "text-tec-success" : "text-tec-amber"}`}>
          {signature ? "Assinatura capturada." : "Peça para o cliente assinar no quadro ao lado."}
        </p>
        <Button className="mt-5 w-full" icon={<RotateCcw size={17} />} onClick={resetCanvas}>
          Limpar assinatura
        </Button>
      </aside>
    </div>
  );
}

function CheckinSuccess({
  created,
  onClose,
  onOpenOrder,
}: {
  created: CheckinResponse;
  onClose: () => void;
  onOpenOrder: (name: string) => void;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
      <section className="rounded-card border border-tec-success/30 bg-tec-success/10 p-5">
        <CheckCircle2 className="text-tec-success" size={28} />
        <h3 className="mt-4 text-2xl font-bold text-white">{created.service_order.name}</h3>
        <p className="mt-2 text-sm text-tec-subtle">
          OS criada em Entrada criada com foto e assinatura de entrada salvas.
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button
            onClick={() => {
              onOpenOrder(created.service_order.name);
              onClose();
            }}
            variant="primary"
          >
            Abrir detalhe da OS
          </Button>
          <Button onClick={onClose}>Fechar</Button>
        </div>
      </section>
      <section className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4">
        <h3 className="text-sm font-bold text-white">Impressão</h3>
        <div className="mt-3 space-y-2">
          {created.service_order.print_links.map((link) => (
            <a
              className="flex min-h-11 items-center justify-between gap-3 rounded-card border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-tec-subtle transition hover:border-tec-orange/50 hover:text-white"
              href={link.url}
              key={link.format}
              rel="noreferrer"
              target="_blank"
            >
              <span>{link.label}</span>
              <Printer className="text-tec-orange" size={17} />
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}

function SectionTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-9 w-9 place-items-center rounded-card bg-tec-orange/15 text-tec-orange">{icon}</span>
      <h3 className="text-base font-bold text-white">{title}</h3>
    </div>
  );
}

function SelectedBox({ lines, onClear }: { lines: string[]; onClear: () => void }) {
  return (
    <div className="mt-3 rounded-card border border-tec-orange/35 bg-tec-orange/10 p-4">
      {lines.map((line) => (
        <p className="text-sm text-tec-subtle first:font-bold first:text-white" key={line}>
          {line}
        </p>
      ))}
      <Button className="mt-4" onClick={onClear}>
        Trocar
      </Button>
    </div>
  );
}

function Field({
  autoComplete,
  inputMode,
  label,
  maxLength,
  onChange,
  placeholder,
  required,
  type = "text",
  value,
}: {
  autoComplete?: HTMLInputAutoCompleteAttribute;
  inputMode?: React.HTMLAttributes<HTMLInputElement>["inputMode"];
  label: string;
  maxLength?: number;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  type?: HTMLInputTypeAttribute;
  value: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 flex items-center justify-between gap-2 text-xs font-bold uppercase text-tec-muted">
        <span>{label}</span>
        <span className={required ? "text-tec-orange" : "text-tec-muted/70"}>{required ? "Obrigatório" : "Opcional"}</span>
      </span>
      <input
        aria-required={required || undefined}
        autoComplete={autoComplete}
        className="h-11 w-full rounded-control border border-tec-border/25 bg-tec-field px-3 text-sm text-white outline-none focus:border-tec-orange/70"
        inputMode={inputMode}
        maxLength={maxLength}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
        type={type}
        value={value}
      />
    </label>
  );
}

function TextArea({
  label,
  onChange,
  required,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  required?: boolean;
  value: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 flex items-center justify-between gap-2 text-xs font-bold uppercase text-tec-muted">
        <span>{label}</span>
        <span className={required ? "text-tec-orange" : "text-tec-muted/70"}>{required ? "Obrigatório" : "Opcional"}</span>
      </span>
      <textarea
        aria-required={required || undefined}
        className="min-h-[190px] w-full resize-none rounded-control border border-tec-border/25 bg-tec-field p-3 text-sm text-white outline-none focus:border-tec-orange/70"
        onChange={(event) => onChange(event.target.value)}
        required={required}
        value={value}
      />
    </label>
  );
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Falha ao ler a foto."));
    reader.onload = () => resolve(String(reader.result));
    reader.readAsDataURL(file);
  });
}

function makeLocalTestPhoto() {
  const canvas = document.createElement("canvas");
  canvas.width = 960;
  canvas.height = 540;
  const context = canvas.getContext("2d");
  if (context) {
    context.fillStyle = "#15181B";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = "#FE5000";
    context.fillRect(0, 0, canvas.width, 76);
    context.fillStyle = "#202428";
    context.font = "bold 34px Space Grotesk, sans-serif";
    context.fillText("TECPONTO - FOTO DE ENTRADA", 32, 50);
    context.fillStyle = "#F5F6F7";
    context.font = "24px Space Grotesk, sans-serif";
    context.fillText(new Date().toLocaleString("pt-BR"), 32, 140);
    context.fillText("Imagem local para teste automatizado do check-in.", 32, 190);
    context.strokeStyle = "#ffffff";
    context.lineWidth = 4;
    context.strokeRect(32, 230, 420, 240);
    context.fillText("Aparelho fotografado no balcão", 64, 360);
  }
  return {
    dataUrl: canvas.toDataURL("image/png"),
    filename: "foto-entrada-teste-local.png",
  };
}
