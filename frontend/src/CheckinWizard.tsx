import {
  type HTMLInputAutoCompleteAttribute,
  type HTMLInputTypeAttribute,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Battery,
  BriefcaseBusiness,
  Building2,
  Camera,
  Check,
  CheckCircle2,
  CircleHelp,
  ClipboardCheck,
  ClipboardList,
  FileText,
  Headphones,
  IdCard,
  Info,
  Mail,
  Mic,
  Monitor,
  PackageCheck,
  PenLine,
  Phone,
  Printer,
  QrCode,
  RotateCcw,
  Search,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Tablet,
  Upload,
  UserRound,
  Watch,
  X,
  Zap,
} from "lucide-react";

import {
  balcao,
  checkin,
  type AcceptanceIssueResponse,
  type CheckinPayload,
  type CheckinResponse,
  type CustomerDeviceSummary,
  type CustomerSummary,
  type DeliverySuggestion,
  type WarrantyCandidate,
} from "./api";
import { ApprovalRequestModal } from "./ApprovalRequestModal";
import { Button } from "./ui";

const steps = ["Cliente", "Aparelho", "Dados", "Fotos", "Assinatura"];
const stepDescriptions = [
  "Identifique ou cadastre o cliente antes de continuar.",
  "Identifique ou cadastre o aparelho vinculado a este cliente.",
  "Registre o relato do cliente e o estado físico do aparelho.",
  "Registre as fotos obrigatórias para validar o check-in.",
  "Revise os dados, confirme as declarações e colete a assinatura.",
];
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

type CustomerMeta = {
  type: string;
  contactPreference: string;
  origin: string;
};

type CustomerMicrostep = "choice" | "existing" | "new";
type DeviceMicrostep = "choice" | "existing" | "new";

type DeviceMeta = {
  type: string;
};

type ServiceSelections = {
  defects: string[];
  problemLocations: string[];
  physicalStates: string[];
  accessories: string[];
  observations: string;
};

const defaultCustomer: NewCustomerForm = {
  customer_name: "",
  mobile_no: "",
  custom_cpf: "",
  custom_rg: "",
  custom_nao_possui_cpf: false,
  email_id: "",
};

const defaultDevice: NewDeviceForm = {
  brand: "",
  model: "",
  color: "",
  imei_serial: "",
  capacity: "",
  general_state: "",
};

const defaultCustomerMeta: CustomerMeta = {
  type: "Pessoa física",
  contactPreference: "WhatsApp",
  origin: "Balcão",
};

const defaultServiceSelections: ServiceSelections = {
  defects: [],
  problemLocations: [],
  physicalStates: [],
  accessories: [],
  observations: "",
};

const customerTypes = [
  { label: "Pessoa física", icon: <UserRound size={20} /> },
  { label: "Empresa", icon: <Building2 size={20} /> },
  { label: "Cliente sem CPF", icon: <IdCard size={20} /> },
  { label: "Cliente recorrente", icon: <RotateCcw size={20} /> },
];

const contactPreferences = [
  { label: "WhatsApp", icon: <Phone size={20} /> },
  { label: "Ligação", icon: <Phone size={20} /> },
  { label: "E-mail", icon: <Mail size={20} /> },
];

const origins = [
  { label: "Balcão", icon: <UserRound size={20} /> },
  { label: "WhatsApp", icon: <Phone size={20} /> },
  { label: "Indicação", icon: <UserRound size={20} /> },
  { label: "Garantia", icon: <ShieldCheck size={20} /> },
  { label: "Retorno", icon: <RotateCcw size={20} /> },
];

const deviceTypes = [
  { label: "Celular", icon: <Smartphone size={18} /> },
  { label: "Tablet", icon: <Tablet size={18} /> },
  { label: "Notebook", icon: <Monitor size={18} /> },
  { label: "Smartwatch", icon: <Watch size={18} /> },
  { label: "Fone", icon: <Headphones size={18} /> },
  { label: "Outro", icon: <CircleHelp size={18} /> },
];

const brands = ["Apple", "Samsung", "Motorola", "Xiaomi", "Lenovo", "Dell", "Outro"];
const capacities = ["64GB", "128GB", "256GB", "512GB", "1TB", "Não sei"];
const colors = ["Preto", "Branco", "Prata", "Azul", "Dourado", "Rosa", "Outro"];

const defectOptions = [
  "Não liga",
  "Não carrega",
  "Carrega intermitente",
  "Aquece",
  "Reinicia sozinho",
  "Tela quebrada",
  "Tela sem imagem",
  "Touch falhando",
  "Sem áudio",
  "Microfone falhando",
  "Câmera falhando",
  "Molhou",
  "Bateria descarregando rápido",
  "Conector com mau contato",
  "Lentidão/travamento",
  "Outro",
];

const locationOptions = [
  "Tela",
  "Bateria",
  "Conector",
  "Placa",
  "Câmera",
  "Alto-falante",
  "Microfone",
  "Botões",
  "Carcaça",
  "Não identificado",
];

const physicalOptions = [
  "Sem trincos aparentes",
  "Tela trincada",
  "Tampa traseira trincada",
  "Marcas leves de uso",
  "Arranhões laterais",
  "Amassado",
  "Oxidação aparente",
  "Aparelho molhado",
  "Parafusos ausentes",
  "Lacre violado",
  "Não liga para conferência",
  "Cliente não soube informar",
];

const accessoryOptions = [
  "Sem acessórios",
  "Carregador",
  "Cabo",
  "Fonte",
  "Capa",
  "Película",
  "Chip",
  "Cartão de memória",
  "Caixa",
  "Nota fiscal",
  "Outro",
];

const damageMarkers = ["trincada", "arranh", "amassado", "oxidação", "molhado", "dano", "lacre", "quebrada"];

interface CheckinWizardProps {
  onClose: () => void;
  onCreated: (response: CheckinResponse) => void;
  onDirtyChange?: (dirty: boolean) => void;
  onOpenOrder: (response: CheckinResponse) => void;
  presentation?: "page";
}

export function CheckinWizard({ onClose, onCreated, onDirtyChange, onOpenOrder, presentation }: CheckinWizardProps) {
  const [step, setStep] = useState(0);
  const [created, setCreated] = useState<CheckinResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [customerQuery, setCustomerQuery] = useState("");
  const [customerRows, setCustomerRows] = useState<CustomerSummary[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerSummary | null>(null);
  const [newCustomer, setNewCustomer] = useState<NewCustomerForm>(defaultCustomer);
  const [customerMeta, setCustomerMeta] = useState<CustomerMeta>(defaultCustomerMeta);
  const [customerMicrostep, setCustomerMicrostep] = useState<CustomerMicrostep>("choice");

  const [deviceQuery, setDeviceQuery] = useState("");
  const [deviceRows, setDeviceRows] = useState<CustomerDeviceSummary[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<CustomerDeviceSummary | null>(null);
  const [newDevice, setNewDevice] = useState<NewDeviceForm>(defaultDevice);
  const [deviceMeta, setDeviceMeta] = useState<DeviceMeta>({ type: "Celular" });
  const [deviceMicrostep, setDeviceMicrostep] = useState<DeviceMicrostep>("choice");

  const [serviceOrder, setServiceOrder] = useState({
    reported_defect: "",
    physical_state: "",
    accessories_received: "",
    estimated_deadline: "",
    lead_time_business_hours: "",
  });
  const [serviceSelections, setServiceSelections] = useState<ServiceSelections>(defaultServiceSelections);
  const [warrantyCandidates, setWarrantyCandidates] = useState<WarrantyCandidate[]>([]);
  const [warrantyLoading, setWarrantyLoading] = useState(false);
  const [originalServiceOrder, setOriginalServiceOrder] = useState("");
  const [deliverySuggestion, setDeliverySuggestion] = useState<DeliverySuggestion | null>(null);
  const [autoSuggestedDeadline, setAutoSuggestedDeadline] = useState("");
  const [photo, setPhoto] = useState<{ dataUrl: string; filename: string } | null>(null);

  const generatedSummary = useMemo(() => buildServiceSummary(serviceSelections), [serviceSelections]);
  const hasDamage = useMemo(
    () =>
      [...serviceSelections.defects, ...serviceSelections.physicalStates].some((value) =>
        damageMarkers.some((marker) => value.toLowerCase().includes(marker)),
      ),
    [serviceSelections],
  );

  useEffect(() => {
    if (!open) {
      return;
    }
    setStep(0);
    setCreated(null);
    setSubmitting(false);
    setError(null);
    setCustomerMicrostep("choice");
    setDeviceMicrostep("choice");
  }, [open]);

  useEffect(() => {
    setServiceOrder((current) => ({
      ...current,
      reported_defect: generatedSummary,
      physical_state: serviceSelections.physicalStates.join("; "),
      accessories_received: serviceSelections.accessories.join("; "),
    }));
  }, [generatedSummary, serviceSelections.accessories, serviceSelections.physicalStates]);

  useEffect(() => {
    if (!open) return;
    const defects = serviceSelections.defects;
    if (!defects.length) {
      setDeliverySuggestion(null);
      setServiceOrder((current) => current.estimated_deadline === autoSuggestedDeadline
        ? { ...current, estimated_deadline: "" }
        : current);
      setAutoSuggestedDeadline("");
      return;
    }
    let cancelled = false;
    const leadTime = Number(serviceOrder.lead_time_business_hours) || 0;
    checkin.getDeliverySuggestion(defects, leadTime).then((suggestion) => {
      if (cancelled) return;
      setDeliverySuggestion(suggestion);
      setServiceOrder((current) => {
        if (!suggestion.suggested_delivery_date || (current.estimated_deadline && current.estimated_deadline !== autoSuggestedDeadline)) {
          return current;
        }
        return { ...current, estimated_deadline: suggestion.suggested_delivery_date };
      });
      setAutoSuggestedDeadline(suggestion.suggested_delivery_date);
    }).catch(() => {
      if (!cancelled) setDeliverySuggestion(null);
    });
    return () => { cancelled = true; };
  }, [autoSuggestedDeadline, open, serviceOrder.lead_time_business_hours, serviceSelections.defects]);

  useEffect(() => {
    const customer = selectedCustomer?.name ?? "";
    const device = selectedDevice?.name ?? "";
    if (!customer && !device) {
      setWarrantyCandidates([]);
      setOriginalServiceOrder("");
      return;
    }
    let cancelled = false;
    setWarrantyLoading(true);
    checkin
      .listWarrantyCandidates(customer, device)
      .then((response) => {
        if (!cancelled) {
          setWarrantyCandidates(response.items);
          setOriginalServiceOrder((current) => (response.items.some((item) => item.name === current) ? current : ""));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setWarrantyCandidates([]);
          setOriginalServiceOrder("");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setWarrantyLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedCustomer?.name, selectedDevice?.name]);

  const customerReady = customerMicrostep !== "choice" && Boolean(
    selectedCustomer ||
      (newCustomer.customer_name.trim() &&
        newCustomer.mobile_no.trim() &&
        (newCustomer.custom_cpf.trim() || (newCustomer.custom_nao_possui_cpf && newCustomer.custom_rg.trim()))),
  );
  const deviceReady = deviceMicrostep !== "choice" && Boolean(
    selectedDevice
      ? selectedDevice.imei_serial
      : newDevice.brand.trim() && newDevice.model.trim() && newDevice.imei_serial.trim(),
  );
  const dataReady = Boolean(serviceSelections.physicalStates.length && serviceOrder.physical_state.trim());
  const photoReady = Boolean(photo?.dataUrl);
  const canContinue = [customerReady, deviceReady, dataReady, photoReady, true][step] ?? false;
  const canGoBack = step > 0 || (step === 0 && customerMicrostep !== "choice") || (step === 1 && deviceMicrostep !== "choice");
  const hasUnsavedChanges = Boolean(
    !created && (
      selectedCustomer || customerQuery.trim() || newCustomer.customer_name.trim() || newCustomer.mobile_no.trim() || newCustomer.custom_cpf.trim() || newCustomer.custom_rg.trim()
      || selectedDevice || deviceQuery.trim() || newDevice.brand.trim() || newDevice.model.trim() || newDevice.imei_serial.trim()
      || serviceOrder.reported_defect.trim() || serviceOrder.physical_state.trim() || serviceOrder.accessories_received.trim() || photo
    ),
  );

  useEffect(() => {
    onDirtyChange?.(hasUnsavedChanges);
    return () => onDirtyChange?.(false);
  }, [hasUnsavedChanges, onDirtyChange]);

  const requestClose = useCallback(() => {
    if (hasUnsavedChanges && !window.confirm("Existem dados nao salvos no check-in. Deseja sair mesmo assim?")) {
      return;
    }
    onClose();
  }, [hasUnsavedChanges, onClose]);

  const goBack = useCallback(() => {
    if (step === 0 && customerMicrostep !== "choice") {
      setCustomerMicrostep("choice");
      return;
    }
    if (step === 1 && deviceMicrostep !== "choice") {
      setDeviceMicrostep("choice");
      return;
    }
    setStep((current) => Math.max(0, current - 1));
  }, [customerMicrostep, deviceMicrostep, step]);

  const searchCustomers = useCallback(async () => {
    setError(null);
    const response = await balcao.searchCustomers(customerQuery, 8);
    setCustomerRows(response.items);
  }, [customerQuery]);

  const searchDevices = useCallback(async () => {
    setError(null);
    const response = await balcao.listDevices(deviceQuery, 8, selectedCustomer?.name ?? "");
    setDeviceRows(response.items);
  }, [deviceQuery, selectedCustomer]);

  async function submit() {
    setError(null);
    if (!photo) {
      setError("A foto de entrada é obrigatória para criar o check-in.");
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
        is_warranty: Boolean(originalServiceOrder),
        original_service_order: originalServiceOrder || undefined,
        defects: serviceSelections.defects,
        estimated_deadline: serviceOrder.estimated_deadline,
        lead_time_business_hours: Number(serviceOrder.lead_time_business_hours) || 0,
      },
      entry_photo: {
        data_url: photo.dataUrl,
        filename: photo.filename,
      },
    };

    setSubmitting(true);
    try {
      const response = await checkin.createServiceOrder(payload);
      setCreated(response);
      onCreated(response);
      onOpenOrder(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao criar a OS.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={presentation === "page" ? "mx-auto max-w-[1480px] space-y-4" : "mx-auto max-w-[1480px]"}>
      {presentation === "page" ? (
        <header className="flex flex-col gap-4 rounded-card border border-tec-border/20 bg-tec-panel px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-control bg-tec-orange/15 text-tec-orange">
              <ClipboardCheck size={22} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-tec-muted">Atendimento</p>
              <h1 className="font-display text-2xl font-bold text-white">{created ? "OS criada" : "Nova OS / check-in"}</h1>
            </div>
          </div>
          <Button icon={<X size={17} />} onClick={requestClose}>Cancelar</Button>
        </header>
      ) : null}
      <div>
        {created ? (
          <CheckinSuccess created={created} onClose={requestClose} onOpenOrder={onOpenOrder} />
        ) : (
          <div className="overflow-hidden rounded-[18px] border border-tec-border/15 bg-tec-panel">
            <div className="border-b border-tec-border/15 px-5 py-5 sm:px-7">
              <WizardStepper step={step} />
            </div>

            <div className="space-y-4 px-5 py-4 sm:px-7">
              <StepStatusBanner step={step} />
              <div className="min-h-[520px]">
                {step === 0 ? (
                  <CustomerStep
                    customerMeta={customerMeta}
                    customerMicrostep={customerMicrostep}
                    customerQuery={customerQuery}
                    customerRows={customerRows}
                    newCustomer={newCustomer}
                    onSearch={searchCustomers}
                    selectedCustomer={selectedCustomer}
                    setCustomerMeta={(value) => {
                      setCustomerMeta(value);
                      if (value.type === "Cliente sem CPF") {
                        setNewCustomer((current) => ({
                          ...current,
                          custom_cpf: "",
                          custom_nao_possui_cpf: true,
                        }));
                      }
                    }}
                    setCustomerMicrostep={setCustomerMicrostep}
                    setCustomerQuery={setCustomerQuery}
                    setNewCustomer={setNewCustomer}
                    setSelectedCustomer={setSelectedCustomer}
                  />
                ) : null}
                {step === 1 ? (
                  <DeviceStep
                    deviceMeta={deviceMeta}
                    deviceMicrostep={deviceMicrostep}
                    deviceQuery={deviceQuery}
                    deviceRows={deviceRows}
                    newDevice={newDevice}
                    onSearch={searchDevices}
                    selectedCustomer={selectedCustomer}
                    selectedDevice={selectedDevice}
                    setDeviceMeta={setDeviceMeta}
                    setDeviceMicrostep={setDeviceMicrostep}
                    setDeviceQuery={setDeviceQuery}
                    setNewDevice={setNewDevice}
                    setSelectedDevice={setSelectedDevice}
                  />
                ) : null}
                {step === 2 ? (
                  <ServiceDataStep
                    deliverySuggestion={deliverySuggestion}
                    generatedSummary={generatedSummary}
                    originalServiceOrder={originalServiceOrder}
                    selections={serviceSelections}
                    serviceOrder={serviceOrder}
                    setServiceOrder={setServiceOrder}
                    warrantyCandidates={warrantyCandidates}
                    warrantyLoading={warrantyLoading}
                    setOriginalServiceOrder={setOriginalServiceOrder}
                    setSelections={setServiceSelections}
                  />
                ) : null}
                {step === 3 ? <PhotoStep hasDamage={hasDamage} photo={photo} setPhoto={setPhoto} /> : null}
                {step === 4 ? (
                  <SignatureStep
                    customer={selectedCustomer}
                    customerForm={newCustomer}
                    device={selectedDevice}
                    deviceForm={newDevice}
                    photo={photo}
                    serviceOrder={serviceOrder}
                  />
                ) : null}
              </div>
            </div>

            {error ? (
              <div className="mx-5 rounded-card border border-tec-red/30 bg-tec-red/10 p-3 text-sm text-tec-red sm:mx-7">
                {error}
              </div>
            ) : null}

            <div className="mt-4 flex flex-col gap-4 border-t border-tec-border/15 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-7">
              <p className="flex items-center gap-3 text-sm text-tec-muted">
                <Info className="shrink-0 text-tec-blue" size={20} />
                A foto fica salva agora. O aceite por selfie e assinatura será coletado no link seguro antes de qualquer avanço técnico.
              </p>
              <div className="flex justify-end gap-3">
                <Button disabled={!canGoBack || submitting} icon={<ArrowLeft size={17} />} onClick={goBack}>
                  Voltar
                </Button>
                {step < steps.length - 1 ? (
                  <Button disabled={!canContinue} icon={<ArrowRight size={17} />} onClick={() => setStep((current) => current + 1)} variant="primary">
                    Avançar
                  </Button>
                ) : (
                  <Button disabled={!canContinue || submitting} icon={<CheckCircle2 size={17} />} onClick={submit} variant="primary">
                    {submitting ? "Criando..." : "Concluir check-in"}
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function WizardStepper({ step }: { step: number }) {
	const icons = [UserRound, Smartphone, ClipboardCheck, Camera, PenLine];

  return (
    <div className="grid grid-cols-5 gap-2 sm:gap-3">
      {steps.map((label, index) => {
        const done = index < step;
        const active = index === step;
        const StepIcon = icons[index];
        return (
          <div className="relative min-w-0 text-center" key={label}>
            {index > 0 ? (
              <span
                className={`absolute right-1/2 top-5 z-0 hidden h-px w-full sm:block ${
                  done ? "bg-tec-success/70" : active ? "bg-tec-orange/70" : "bg-tec-border/50"
                }`}
              />
            ) : null}
            <span
              className={`relative z-10 mx-auto grid h-10 w-10 place-items-center rounded-full border text-sm font-bold ${
                done
                  ? "border-tec-success bg-tec-success/10 text-tec-success"
                  : active
                    ? "border-tec-orange bg-tec-orange/10 text-tec-orange"
                    : "border-tec-border/20 bg-tec-field text-tec-muted"
              }`}
            >
              {done ? <Check size={18} /> : <StepIcon size={18} />}
            </span>
            <span className={`mt-2 block min-w-0 truncate text-[11px] font-semibold sm:text-sm ${done ? "text-tec-success" : active ? "text-tec-orange" : "text-tec-muted"}`}>
              {label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function StepStatusBanner({ step }: { step: number }) {
  return (
    <div className="flex flex-col gap-3 rounded-card border border-tec-border/15 bg-tec-field/70 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
      <p className="text-tec-muted">
        <span className="font-semibold text-white">Etapa {step + 1} de 5</span>
        <span className="mx-2">•</span>
        {stepDescriptions[step]}
      </p>
      <span className="inline-flex w-fit items-center gap-2 rounded-control border border-tec-border/15 bg-tec-panel-strong px-3 py-2 text-xs font-semibold text-tec-blue">
        <Info size={15} />
        Campos obrigatórios
      </span>
    </div>
  );
}

function CustomerStep({
  customerMeta,
  customerMicrostep,
  customerQuery,
  customerRows,
  newCustomer,
  onSearch,
  selectedCustomer,
  setCustomerMeta,
  setCustomerMicrostep,
  setCustomerQuery,
  setNewCustomer,
  setSelectedCustomer,
}: {
  customerMeta: CustomerMeta;
  customerMicrostep: CustomerMicrostep;
  customerQuery: string;
  customerRows: CustomerSummary[];
  newCustomer: NewCustomerForm;
  onSearch: () => void;
  selectedCustomer: CustomerSummary | null;
  setCustomerMeta: (value: CustomerMeta) => void;
  setCustomerMicrostep: (value: CustomerMicrostep) => void;
  setCustomerQuery: (value: string) => void;
  setNewCustomer: (value: NewCustomerForm | ((current: NewCustomerForm) => NewCustomerForm)) => void;
  setSelectedCustomer: (value: CustomerSummary | null) => void;
}) {
  const updateCustomer = (patch: Partial<NewCustomerForm>) => {
    setNewCustomer((current) => ({ ...current, ...patch }));
  };

  if (customerMicrostep === "choice") {
    return (
      <div className="space-y-4">
        <InfoBanner
          icon={<UserRound size={26} />}
          title="Primeiro, diga se o cliente já existe ou se é um cadastro novo."
          text="O balcão segue por decisão: escolha um caminho, depois a tela mostra só o que importa."
        />
        <div className="grid gap-4 lg:grid-cols-2">
          <MicrostepChoiceCard
            compact
            icon={<Search size={28} />}
            label="Cliente existente"
            onClick={() => {
              setCustomerMicrostep("existing");
              setSelectedCustomer(null);
            }}
            text="Buscar por nome, telefone, CPF ou RG e vincular a OS ao cadastro já existente."
          />
          <MicrostepChoiceCard
            compact
            icon={<UserRound size={28} />}
            label="Cliente novo"
            onClick={() => {
              setCustomerMicrostep("new");
              setSelectedCustomer(null);
            }}
            text="Criar o cadastro mínimo obrigatório: nome, WhatsApp e CPF ou RG quando não possuir CPF."
          />
        </div>
      </div>
    );
  }

  if (customerMicrostep === "existing") {
    return (
      <WizardCard>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <SectionTitle icon={<Search size={21} />} title="Buscar cliente existente" />
          <Button icon={<ArrowLeft size={17} />} onClick={() => setCustomerMicrostep("choice")} variant="secondary">
            Trocar caminho
          </Button>
        </div>
        <div className="mt-5 flex gap-3">
          <input
            className="h-12 flex-1 rounded-control border border-tec-border/15 bg-tec-field px-4 text-sm text-white outline-none placeholder:text-tec-muted focus:border-tec-orange/70"
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
          <Button icon={<Search size={18} />} onClick={() => void onSearch()} variant="primary">
            Buscar
          </Button>
        </div>
        <div className="mt-4 rounded-card border border-dashed border-tec-border/15 bg-tec-panel/50 p-4">
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
          ) : customerRows.length ? (
            <div className="space-y-2">
              {customerRows.map((customer) => (
                <button
                  className="w-full rounded-card border border-tec-border/15 bg-tec-field p-3 text-left text-sm transition hover:border-tec-orange/50"
                  key={customer.name}
                  onClick={() => setSelectedCustomer(customer)}
                  type="button"
                >
                  <span className="block font-bold text-white">{customer.customer_name ?? customer.name}</span>
                  <span className="mt-1 block text-xs text-tec-muted">
                    {[customer.mobile_no, customer.custom_cpf || customer.custom_rg, customer.email_id].filter(Boolean).join(" • ") || customer.name}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<UserRound size={34} />}
              subtitle="Busque um cliente existente. Se não encontrar, volte e escolha Cliente novo."
              title="Nenhum cliente selecionado"
            />
          )}
        </div>
      </WizardCard>
    );
  }

  if (customerMicrostep === "new") {
    return (
      <div className="space-y-4">
        <WizardCard clean>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <SectionTitle icon={<UserRound size={21} />} title="Criar cliente novo" />
              <p className="mt-2 text-sm text-tec-muted">Cadastro mínimo para abrir OS no balcão.</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge>Campos obrigatórios</Badge>
              <Button icon={<ArrowLeft size={17} />} onClick={() => setCustomerMicrostep("choice")} variant="secondary">
                Trocar caminho
              </Button>
            </div>
          </div>
          <div className="mt-5 rounded-card border border-tec-orange/30 bg-tec-orange/[0.045] p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <p className="text-sm font-bold text-white">Dados essenciais</p>
              <span className="text-xs font-bold uppercase text-tec-orange">Obrigatorios para abrir a OS</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Field
                autoComplete="name"
                label="Nome completo"
                onChange={(value) => updateCustomer({ customer_name: value })}
                placeholder="Digite o nome completo"
                required
                value={newCustomer.customer_name}
              />
            </div>
            <Field
              autoComplete="tel"
              inputMode="tel"
              label="Telefone / WhatsApp"
              onChange={(value) => updateCustomer({ mobile_no: value })}
              placeholder="(11) 99999-9999"
              required
              type="tel"
              value={newCustomer.mobile_no}
            />
            {newCustomer.custom_nao_possui_cpf ? (
              <Field
                autoComplete="off"
                label="RG"
                onChange={(value) => updateCustomer({ custom_rg: value })}
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
                onChange={(value) => updateCustomer({ custom_cpf: value })}
                placeholder="000.000.000-00"
                required
                value={newCustomer.custom_cpf}
              />
            )}
            </div>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Field
                autoComplete="email"
                inputMode="email"
                label="E-mail"
                onChange={(value) => updateCustomer({ email_id: value })}
                placeholder="cliente@email.com"
                type="email"
                value={newCustomer.email_id}
              />
            </div>
            <label className="sm:col-span-2 flex cursor-pointer items-center gap-3 text-sm font-semibold text-tec-subtle">
              <input
                checked={newCustomer.custom_nao_possui_cpf}
                className="h-5 w-5 rounded border-tec-border/25 bg-tec-field accent-tec-orange"
                onChange={(event) =>
                  updateCustomer({
                    custom_cpf: "",
                    custom_nao_possui_cpf: event.currentTarget.checked,
                  })
                }
                type="checkbox"
              />
              Cliente não possui CPF
            </label>
          </div>
        </WizardCard>

        <WizardCard clean className="p-4">
          <p className="mb-4 text-sm font-bold text-white">Informacoes complementares</p>
          <div className="grid gap-4 lg:grid-cols-[1fr_1fr_1.35fr]">
          <ChoicePanel compact label="Tipo de cliente">
            {customerTypes.map((option) => (
              <OptionCard
                active={customerMeta.type === option.label}
                icon={option.icon}
                key={option.label}
                label={option.label}
                onClick={() => {
                  setCustomerMeta({ ...customerMeta, type: option.label });
                  if (option.label === "Cliente sem CPF") {
                    updateCustomer({ custom_cpf: "", custom_nao_possui_cpf: true });
                  }
                }}
              />
            ))}
          </ChoicePanel>
          <ChoicePanel compact label="Preferência de contato">
            {contactPreferences.map((option) => (
              <OptionCard
                active={customerMeta.contactPreference === option.label}
                icon={option.icon}
                key={option.label}
                label={option.label}
                onClick={() => setCustomerMeta({ ...customerMeta, contactPreference: option.label })}
              />
            ))}
          </ChoicePanel>
          <ChoicePanel compact label="Origem do atendimento">
            {origins.map((option) => (
              <OptionCard
                active={customerMeta.origin === option.label}
                icon={option.icon}
                key={option.label}
                label={option.label}
                onClick={() => setCustomerMeta({ ...customerMeta, origin: option.label })}
              />
            ))}
          </ChoicePanel>
          </div>
        </WizardCard>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(420px,1fr)]">
        <WizardCard>
          <SectionTitle icon={<Search size={21} />} title="Buscar cliente" />
          <div className="mt-5 flex gap-3">
            <input
              className="h-12 flex-1 rounded-control border border-tec-border/15 bg-tec-field px-4 text-sm text-white outline-none placeholder:text-tec-muted focus:border-tec-orange/70"
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
            <Button icon={<Search size={18} />} onClick={() => void onSearch()} variant="primary">
              Buscar
            </Button>
          </div>

          <div className="mt-4 rounded-card border border-dashed border-tec-border/15 bg-tec-panel/50 p-4">
            {customerRows.length ? (
              <div className="space-y-2">
                {customerRows.map((customer) => (
                  <button
                    className={`w-full rounded-card border p-3 text-left text-sm transition ${
                      selectedCustomer?.name === customer.name
                        ? "border-tec-orange bg-tec-orange/10"
                        : "border-tec-border/15 bg-tec-field hover:border-tec-orange/50"
                    }`}
                    key={customer.name}
                    onClick={() => setSelectedCustomer(customer)}
                    type="button"
                  >
                    <span className="block font-bold text-white">{customer.customer_name ?? customer.name}</span>
                    <span className="mt-1 block text-xs text-tec-muted">
                      {[customer.mobile_no, customer.custom_cpf || customer.custom_rg, customer.email_id].filter(Boolean).join(" • ") || customer.name}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<UserRound size={34} />}
                subtitle="Busque um cliente existente ou crie um novo para continuar."
                title={selectedCustomer ? selectedCustomer.customer_name ?? selectedCustomer.name : "Nenhum cliente selecionado"}
              />
            )}
          </div>
        </WizardCard>

        <WizardCard>
          <div className="flex items-start justify-between gap-3">
            <SectionTitle icon={<UserRound size={21} />} title={selectedCustomer ? "Cliente selecionado" : "Criar cliente"} />
            {!selectedCustomer ? <Badge>Campos obrigatórios</Badge> : null}
          </div>
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
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Field
                  autoComplete="name"
                  label="Nome completo"
                  onChange={(value) => updateCustomer({ customer_name: value })}
                  placeholder="Digite o nome completo"
                  required
                  value={newCustomer.customer_name}
                />
              </div>
              <Field
                autoComplete="tel"
                inputMode="tel"
                label="Telefone / WhatsApp"
                onChange={(value) => updateCustomer({ mobile_no: value })}
                placeholder="(11) 99999-9999"
                required
                type="tel"
                value={newCustomer.mobile_no}
              />
              {newCustomer.custom_nao_possui_cpf ? (
                <Field
                  autoComplete="off"
                  label="RG"
                  onChange={(value) => updateCustomer({ custom_rg: value })}
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
                  onChange={(value) => updateCustomer({ custom_cpf: value })}
                  placeholder="000.000.000-00"
                  required
                  value={newCustomer.custom_cpf}
                />
              )}
              <div className="sm:col-span-2">
                <Field
                  autoComplete="email"
                  inputMode="email"
                  label="E-mail"
                  onChange={(value) => updateCustomer({ email_id: value })}
                  placeholder="cliente@email.com"
                  type="email"
                  value={newCustomer.email_id}
                />
              </div>
              <label className="sm:col-span-2 flex cursor-pointer items-center gap-3 text-sm font-semibold text-tec-subtle">
                <input
                  checked={newCustomer.custom_nao_possui_cpf}
                  className="h-5 w-5 rounded border-tec-border/25 bg-tec-field accent-tec-orange"
                  onChange={(event) =>
                    updateCustomer({
                      custom_cpf: "",
                      custom_nao_possui_cpf: event.currentTarget.checked,
                    })
                  }
                  type="checkbox"
                />
                Cliente não possui CPF
              </label>
            </div>
          )}
        </WizardCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr_1.35fr]">
        <ChoicePanel label="Tipo de cliente">
          {customerTypes.map((option) => (
            <OptionCard
              active={customerMeta.type === option.label}
              icon={option.icon}
              key={option.label}
              label={option.label}
              onClick={() => {
                setCustomerMeta({ ...customerMeta, type: option.label });
                if (option.label === "Cliente sem CPF") {
                  updateCustomer({ custom_cpf: "", custom_nao_possui_cpf: true });
                }
              }}
            />
          ))}
        </ChoicePanel>
        <ChoicePanel label="Preferência de contato">
          {contactPreferences.map((option) => (
            <OptionCard
              active={customerMeta.contactPreference === option.label}
              icon={option.icon}
              key={option.label}
              label={option.label}
              onClick={() => setCustomerMeta({ ...customerMeta, contactPreference: option.label })}
            />
          ))}
        </ChoicePanel>
        <ChoicePanel label="Origem do atendimento">
          {origins.map((option) => (
            <OptionCard
              active={customerMeta.origin === option.label}
              icon={option.icon}
              key={option.label}
              label={option.label}
              onClick={() => setCustomerMeta({ ...customerMeta, origin: option.label })}
            />
          ))}
        </ChoicePanel>
      </div>
    </div>
  );
}

function DeviceStep({
  deviceMeta,
  deviceMicrostep,
  deviceQuery,
  deviceRows,
  newDevice,
  onSearch,
  selectedCustomer,
  selectedDevice,
  setDeviceMeta,
  setDeviceMicrostep,
  setDeviceQuery,
  setNewDevice,
  setSelectedDevice,
}: {
  deviceMeta: DeviceMeta;
  deviceMicrostep: DeviceMicrostep;
  deviceQuery: string;
  deviceRows: CustomerDeviceSummary[];
  newDevice: NewDeviceForm;
  onSearch: () => void;
  selectedCustomer: CustomerSummary | null;
  selectedDevice: CustomerDeviceSummary | null;
  setDeviceMeta: (value: DeviceMeta) => void;
  setDeviceMicrostep: (value: DeviceMicrostep) => void;
  setDeviceQuery: (value: string) => void;
  setNewDevice: (value: NewDeviceForm | ((current: NewDeviceForm) => NewDeviceForm)) => void;
  setSelectedDevice: (value: CustomerDeviceSummary | null) => void;
}) {
  const updateDevice = (patch: Partial<NewDeviceForm>) => {
    setNewDevice((current) => ({ ...current, ...patch }));
  };

  if (deviceMicrostep === "choice") {
    return (
      <div className="space-y-4">
        <InfoBanner
          icon={<Smartphone size={26} />}
          title="Agora escolha se o aparelho já está cadastrado ou se é um novo aparelho."
          text="O IMEI continua obrigatório pelo motor; aqui o atendente só escolhe o melhor caminho antes de preencher."
        />
        <div className="grid gap-4 lg:grid-cols-2">
          <MicrostepChoiceCard
            compact
            icon={<Search size={28} />}
            label="Aparelho existente"
            onClick={() => {
              setDeviceMicrostep("existing");
              setSelectedDevice(null);
            }}
            text="Buscar por modelo, IMEI ou serial entre os aparelhos já vinculados ao cliente."
          />
          <MicrostepChoiceCard
            compact
            icon={<Smartphone size={28} />}
            label="Novo aparelho"
            onClick={() => {
              setDeviceMicrostep("new");
              setSelectedDevice(null);
            }}
            text="Cadastrar aparelho com modelo, IMEI/serial e seleções rápidas de marca, capacidade e cor."
          />
        </div>
      </div>
    );
  }

  if (deviceMicrostep === "existing") {
    return (
      <WizardCard clean>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <SectionTitle icon={<Search size={21} />} title="Buscar aparelho existente" />
          <Button icon={<ArrowLeft size={17} />} onClick={() => setDeviceMicrostep("choice")} variant="secondary">
            Trocar caminho
          </Button>
        </div>
        <div className="mt-5 flex gap-3">
          <input
            className="h-12 flex-1 rounded-control border border-tec-border/15 bg-tec-field px-4 text-sm text-white outline-none placeholder:text-tec-muted focus:border-tec-orange/70"
            onChange={(event) => setDeviceQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void onSearch();
              }
            }}
            placeholder="Modelo, IMEI ou serial"
            value={deviceQuery}
          />
          <Button icon={<Search size={18} />} onClick={() => void onSearch()} variant="primary">
            Buscar
          </Button>
        </div>
        <div className="mt-4 rounded-card border border-dashed border-tec-border/15 bg-tec-panel/50 p-4">
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
          ) : deviceRows.length ? (
            <div className="space-y-2">
              {deviceRows.map((device) => (
                <button
                  className="w-full rounded-card border border-tec-border/15 bg-tec-field p-3 text-left text-sm transition hover:border-tec-orange/50"
                  key={device.name}
                  onClick={() => setSelectedDevice(device)}
                  type="button"
                >
                  <span className="block font-bold text-white">{[device.brand, device.model, device.color].filter(Boolean).join(" ") || device.name}</span>
                  <span className="mt-1 block text-xs text-tec-muted">{[device.imei_serial, device.capacity, device.name].filter(Boolean).join(" • ")}</span>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<Smartphone size={34} />}
              subtitle={selectedCustomer ? "Busque o aparelho existente. Se não encontrar, volte e escolha Novo aparelho." : "A busca fica melhor quando o cliente já foi selecionado."}
              title="Nenhum aparelho selecionado"
            />
          )}
        </div>
      </WizardCard>
    );
  }

  if (deviceMicrostep === "new") {
    return (
      <WizardCard clean>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <SectionTitle icon={<Smartphone size={21} />} title="Cadastrar novo aparelho" />
            <p className="mt-2 text-sm text-tec-muted">O IMEI/serial é obrigatório para abrir a OS.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge>Campos obrigatórios</Badge>
            <Button icon={<ArrowLeft size={17} />} onClick={() => setDeviceMicrostep("choice")} variant="secondary">
              Trocar caminho
            </Button>
          </div>
        </div>
        <div className="mt-5 space-y-4">
          <div className="rounded-card border border-tec-orange/30 bg-tec-orange/[0.045] p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <p className="text-sm font-bold text-white">Identificacao do aparelho</p>
              <span className="text-xs font-bold uppercase text-tec-orange">IMEI obrigatorio</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Modelo" onChange={(value) => updateDevice({ model: value })} placeholder="Modelo do aparelho" required value={newDevice.model} />
            <Field
              autoComplete="off"
              highlight
              inputMode="numeric"
              label="IMEI / Serial"
              maxLength={18}
              onChange={(value) => updateDevice({ imei_serial: value })}
              placeholder="15 dígitos do IMEI ou serial"
              required
              value={newDevice.imei_serial}
            />
            </div>
          </div>
          <div className="rounded-card border border-tec-border/15 bg-tec-field/45 p-4">
            <p className="mb-4 text-sm font-bold text-white">Caracteristicas do aparelho</p>
            <div className="space-y-4">
          <ChipGroup label="Tipo de aparelho" required>
            {deviceTypes.map((option) => (
              <OptionChip
                active={deviceMeta.type === option.label}
                icon={option.icon}
                key={option.label}
                label={option.label}
                onClick={() => setDeviceMeta({ type: option.label })}
              />
            ))}
          </ChipGroup>
          <ChipGroup label="Marca" required>
            {brands.map((brand) => (
              <OptionChip
                active={newDevice.brand === brand}
                icon={brand === "Apple" ? <Smartphone size={16} /> : undefined}
                key={brand}
                label={brand}
                onClick={() => updateDevice({ brand: brand === "Outro" ? "" : brand })}
              />
            ))}
          </ChipGroup>
          <ChipGroup label="Capacidade" required>
            {capacities.map((capacity) => (
              <OptionChip
                active={newDevice.capacity === capacity}
                key={capacity}
                label={capacity}
                onClick={() => updateDevice({ capacity: capacity === "Não sei" ? "" : capacity })}
              />
            ))}
          </ChipGroup>
          <ChipGroup label="Cor">
            {colors.map((color) => (
              <ColorChip
                active={newDevice.color === color}
                color={color}
                key={color}
                onClick={() => updateDevice({ color: color === "Outro" ? "" : color })}
              />
            ))}
          </ChipGroup>
            </div>
          </div>
          <TextArea
            label="Estado geral do aparelho"
            maxLength={300}
            onChange={(value) => updateDevice({ general_state: value })}
            placeholder="Descreva o estado geral do aparelho (riscos, detalhes, funcionamento...)"
            value={newDevice.general_state}
          />
        </div>
      </WizardCard>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,0.72fr)_minmax(0,1.08fr)]">
      <WizardCard>
        <SectionTitle icon={<Search size={21} />} title="Buscar aparelho" />
        <div className="mt-5 flex gap-3">
          <input
            className="h-12 flex-1 rounded-control border border-tec-border/15 bg-tec-field px-4 text-sm text-white outline-none placeholder:text-tec-muted focus:border-tec-orange/70"
            onChange={(event) => setDeviceQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void onSearch();
              }
            }}
            placeholder="Modelo, IMEI ou serial"
            value={deviceQuery}
          />
          <Button icon={<Search size={18} />} onClick={() => void onSearch()} variant="primary">
            Buscar
          </Button>
        </div>
        <div className="mt-4 rounded-card border border-dashed border-tec-border/15 bg-tec-panel/50 p-4">
          {deviceRows.length ? (
            <div className="space-y-2">
              {deviceRows.map((device) => (
                <button
                  className={`w-full rounded-card border p-3 text-left text-sm transition ${
                    selectedDevice?.name === device.name
                      ? "border-tec-orange bg-tec-orange/10"
                      : "border-tec-border/15 bg-tec-field hover:border-tec-orange/50"
                  }`}
                  key={device.name}
                  onClick={() => setSelectedDevice(device)}
                  type="button"
                >
                  <span className="block font-bold text-white">{[device.brand, device.model, device.color].filter(Boolean).join(" ") || device.name}</span>
                  <span className="mt-1 block text-xs text-tec-muted">{[device.imei_serial, device.capacity, device.name].filter(Boolean).join(" • ")}</span>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<Smartphone size={34} />}
              subtitle={selectedCustomer ? "Busque um aparelho existente ou crie um novo para continuar." : "Selecione ou cadastre o aparelho vinculado ao atendimento."}
              title={selectedDevice ? selectedDevice.model ?? selectedDevice.name : "Nenhum aparelho selecionado"}
            />
          )}
        </div>
      </WizardCard>

      <WizardCard>
        <div className="flex items-start justify-between gap-3">
          <SectionTitle icon={<Smartphone size={21} />} title={selectedDevice ? "Aparelho selecionado" : "Criar aparelho"} />
          {!selectedDevice ? <Badge>Campos obrigatórios</Badge> : null}
        </div>
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
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Modelo" onChange={(value) => updateDevice({ model: value })} placeholder="Modelo do aparelho" required value={newDevice.model} />
              <Field
                autoComplete="off"
                inputMode="numeric"
                label="IMEI / Serial"
                maxLength={18}
                onChange={(value) => updateDevice({ imei_serial: value })}
                placeholder="15 dígitos do IMEI ou serial"
                required
                value={newDevice.imei_serial}
              />
            </div>
            <ChipGroup label="Tipo de aparelho" required>
              {deviceTypes.map((option) => (
                <OptionChip
                  active={deviceMeta.type === option.label}
                  icon={option.icon}
                  key={option.label}
                  label={option.label}
                  onClick={() => setDeviceMeta({ type: option.label })}
                />
              ))}
            </ChipGroup>
            <ChipGroup label="Marca" required>
              {brands.map((brand) => (
                <OptionChip
                  active={newDevice.brand === brand}
                  icon={brand === "Apple" ? <Smartphone size={16} /> : undefined}
                  key={brand}
                  label={brand}
                  onClick={() => updateDevice({ brand: brand === "Outro" ? "" : brand })}
                />
              ))}
            </ChipGroup>
            <ChipGroup label="Capacidade" required>
              {capacities.map((capacity) => (
                <OptionChip
                  active={newDevice.capacity === capacity}
                  key={capacity}
                  label={capacity}
                  onClick={() => updateDevice({ capacity: capacity === "Não sei" ? "" : capacity })}
                />
              ))}
            </ChipGroup>
            <ChipGroup label="Cor">
              {colors.map((color) => (
                <ColorChip
                  active={newDevice.color === color}
                  color={color}
                  key={color}
                  onClick={() => updateDevice({ color: color === "Outro" ? "" : color })}
                />
              ))}
            </ChipGroup>
            <TextArea
              label="Estado geral do aparelho"
              maxLength={300}
              onChange={(value) => updateDevice({ general_state: value })}
              placeholder="Descreva o estado geral do aparelho (riscos, detalhes, funcionamento...)"
              value={newDevice.general_state}
            />
          </div>
        )}
      </WizardCard>
    </div>
  );
}

function ServiceDataStep({
  deliverySuggestion,
  generatedSummary,
  originalServiceOrder,
  selections,
  serviceOrder,
  setOriginalServiceOrder,
  setServiceOrder,
  setSelections,
  warrantyCandidates,
  warrantyLoading,
}: {
  deliverySuggestion: DeliverySuggestion | null;
  generatedSummary: string;
  originalServiceOrder: string;
  selections: ServiceSelections;
  serviceOrder: {
    reported_defect: string;
    physical_state: string;
    accessories_received: string;
    estimated_deadline: string;
    lead_time_business_hours: string;
  };
  setOriginalServiceOrder: (value: string) => void;
  setServiceOrder: (value: { reported_defect: string; physical_state: string; accessories_received: string; estimated_deadline: string; lead_time_business_hours: string } | ((current: { reported_defect: string; physical_state: string; accessories_received: string; estimated_deadline: string; lead_time_business_hours: string }) => { reported_defect: string; physical_state: string; accessories_received: string; estimated_deadline: string; lead_time_business_hours: string })) => void;
  setSelections: (value: ServiceSelections | ((current: ServiceSelections) => ServiceSelections)) => void;
  warrantyCandidates: WarrantyCandidate[];
  warrantyLoading: boolean;
}) {
  const toggle = (key: keyof Omit<ServiceSelections, "observations">, value: string) => {
    setSelections((current) => {
      const exists = current[key].includes(value);
      const next = exists ? current[key].filter((item) => item !== value) : [...current[key], value];
      return { ...current, [key]: next };
    });
  };

  return (
    <div className="space-y-4">
      <WizardCard clean>
        <SectionTitle icon={<ShieldCheck size={21} />} title="Retrabalho em garantia" />
        {warrantyLoading ? (
          <p className="mt-3 text-sm text-tec-muted">Verificando reparos entregues deste cliente/aparelho...</p>
        ) : warrantyCandidates.length ? (
          <div className="mt-3 space-y-3">
            <p className="text-sm leading-6 text-tec-subtle">
              Este aparelho possui reparo entregue dentro da garantia. Pode ser um retrabalho? Selecione a OS original para registrar a vinculação.
            </p>
            <div className="grid gap-2 lg:grid-cols-2">
              {warrantyCandidates.map((candidate) => {
                const active = originalServiceOrder === candidate.name;
                return (
                  <button
                    className={`rounded-control border p-3 text-left transition ${
                      active ? "border-tec-orange bg-tec-orange/10" : "border-tec-border/20 bg-tec-field hover:border-tec-orange/55"
                    }`}
                    key={candidate.name}
                    onClick={() => setOriginalServiceOrder(active ? "" : candidate.name)}
                    type="button"
                  >
                    <span className="block text-sm font-bold text-white">Garantia da {candidate.name}</span>
                    <span className="mt-1 block line-clamp-2 text-xs text-tec-muted">{candidate.reported_defect || "Reparo anterior entregue"}</span>
                    <span className="mt-2 block text-xs font-semibold text-tec-success">Garantia at{"\u00e9"} {formatShortDate(candidate.warranty_expiry)}</span>
                  </button>
                );
              })}
            </div>
            {originalServiceOrder ? (
              <p className="rounded-control border border-tec-success/25 bg-tec-success/10 px-3 py-2 text-sm font-semibold text-tec-success">
                OS em garantia vinculada a {originalServiceOrder}. M{"\u00e3"}o de obra ficar{"\u00e1"} zerada; pe{"\u00e7"}as continuam com reserva e baixa normal de estoque.
              </p>
            ) : null}
          </div>
        ) : (
          <p className="mt-3 text-sm leading-6 text-tec-muted">
            Nenhuma OS entregue com garantia vigente foi encontrada para este cliente/aparelho. Garantia-cortesia exige libera{"\u00e7"}{"\u00e3"}o do Gestor.
          </p>
        )}
      </WizardCard>

      <InfoBanner
        title="Seleções mais precisas geram orçamentos mais assertivos e execuções técnicas mais alinhadas."
        text="Quanto mais detalhe você registrar agora, menos dúvidas no orçamento e mais agilidade no reparo."
      />

      <WizardCard clean className="p-4">
        <SectionTitle icon={<ClipboardList size={21} />} title="Previsão de entrega" />
        <p className="mt-3 text-sm leading-6 text-tec-muted">
          Ao selecionar um defeito com serviço mapeado, o motor sugere uma data usando os SLAs internos e dias úteis. Ela é apenas uma previsão: pode ser ajustada ou deixada em branco sem impedir a abertura da OS.
        </p>
        {!selections.defects.length ? (
          <p className="mt-3 rounded-control border border-tec-border/20 bg-tec-field/55 px-3 py-2 text-sm text-tec-muted">
            Selecione ao menos um defeito para estimar a entrega. Você ainda pode preencher ou deixar a data em branco.
          </p>
        ) : deliverySuggestion?.mapped_services.length ? (
          <div className="mt-3 rounded-control border border-tec-success/25 bg-tec-success/10 px-3 py-2 text-sm text-tec-subtle">
            <span className="font-semibold text-tec-success">Sugestão do catálogo:</span>{" "}
            {deliverySuggestion.mapped_services.map((service) => service.service_name).join(", ")}.{" "}
            {deliverySuggestion.service_business_hours}h úteis de serviço somados ao fluxo interno.
          </div>
        ) : (
          <p className="mt-3 rounded-control border border-tec-border/20 bg-tec-field/55 px-3 py-2 text-sm text-tec-muted">
            Os defeitos selecionados ainda não possuem um serviço mapeado. A OS continua podendo ser aberta sem previsão.
          </p>
        )}
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Field
            label="Data prometida ao cliente"
            onChange={(value) => setServiceOrder((current) => ({ ...current, estimated_deadline: value }))}
            type="date"
            value={serviceOrder.estimated_deadline}
          />
          <Field
            inputMode="decimal"
            label="Prazo da peça (horas úteis)"
            onChange={(value) => setServiceOrder((current) => ({ ...current, lead_time_business_hours: value.replace(/[^0-9.,]/g, "").replace(",", ".") }))}
            placeholder="Opcional, ex.: 18"
            value={serviceOrder.lead_time_business_hours}
          />
        </div>
      </WizardCard>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <WizardCard clean>
          <ChipGroup compact label="Defeito relatado" multiple>
            {defectOptions.map((defect) => (
              <OptionChip
                active={selections.defects.includes(defect)}
                icon={defectIcon(defect)}
                key={defect}
                label={defect}
                onClick={() => toggle("defects", defect)}
              />
            ))}
          </ChipGroup>
          <div className="mt-4">
            <ChipGroup compact label="Acessórios recebidos" multiple>
              {accessoryOptions.map((accessory) => (
                <OptionChip
                  active={selections.accessories.includes(accessory)}
                  icon={accessory === "Sem acessórios" ? <CircleHelp size={16} /> : <PackageCheck size={16} />}
                  key={accessory}
                  label={accessory}
                  onClick={() => toggle("accessories", accessory)}
                />
              ))}
            </ChipGroup>
          </div>
        </WizardCard>

        <div className="space-y-4">
          <WizardCard clean>
            <ChipGroup compact label="Local do problema" multiple>
              {locationOptions.map((location) => (
                <OptionChip
                  active={selections.problemLocations.includes(location)}
                  icon={locationIcon(location)}
                  key={location}
                  label={location}
                  onClick={() => toggle("problemLocations", location)}
                />
              ))}
            </ChipGroup>
          </WizardCard>

          <WizardCard clean>
            <CheckboxGrid compact label="Estado físico declarado" required>
              {physicalOptions.map((state) => (
                <CheckboxOption
                  active={selections.physicalStates.includes(state)}
                  key={state}
                  label={state}
                  onClick={() => toggle("physicalStates", state)}
                />
              ))}
            </CheckboxGrid>
          </WizardCard>

          <WizardCard clean>
            <SectionTitle icon={<Sparkles size={21} />} title="Resumo gerado automaticamente" />
            <p className="mt-4 whitespace-pre-line text-sm leading-6 text-tec-subtle">
              {generatedSummary || "Selecione defeitos e estado físico para gerar o resumo da OS."}
            </p>
          </WizardCard>
        </div>
      </div>

      <TextArea
        label="Observações adicionais"
        maxLength={500}
        onChange={(value) => setSelections((current) => ({ ...current, observations: value }))}
        placeholder="Descreva detalhes adicionais informados pelo cliente ou observações relevantes..."
        value={selections.observations}
      />
    </div>
  );
}

function PhotoStep({
  hasDamage,
  photo,
  setPhoto,
}: {
  hasDamage: boolean;
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

  const photoSlots = [
    { label: "Frente do aparelho", required: true },
    { label: "Verso do aparelho", required: true },
    { label: "Laterais", required: true },
    { label: "Tela ligada/desligada", required: true },
    { label: "Conector de carga", required: true },
    { label: "Acessórios recebidos", required: false },
    { label: "Dano aparente", required: hasDamage },
    { label: "Número de série / IMEI", required: false },
  ];

  return (
    <div className="space-y-4">
      <InfoBanner
        icon={<Camera size={26} />}
        title="Fotos claras e completas reduzem conflitos e agilizam a análise técnica."
        text="Registre a foto de entrada para validar o check-in e documentar o estado recebido."
      />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <WizardCard className="hidden">
          <SectionTitle icon={<ClipboardList size={21} />} title="Checklist de fotos" />
          <div className="mt-4 space-y-2">
            {photoSlots.map((slot) => (
              <div
                className={`flex min-h-12 items-center justify-between gap-3 rounded-control border px-3 ${
                  photo
                    ? "border-tec-success/25 bg-tec-success/8"
                    : slot.required
                      ? "border-tec-border/15 bg-tec-field"
                      : "border-tec-border/15 bg-tec-panel/50"
                }`}
                key={slot.label}
              >
                <span className="flex items-center gap-3 text-sm font-semibold text-white">
                  {photo ? <CheckCircle2 className="text-tec-success" size={17} /> : <Smartphone className="text-tec-muted" size={17} />}
                  {slot.label}
                </span>
                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${slot.required ? "bg-tec-orange/10 text-tec-orange" : "bg-tec-blue/10 text-tec-blue"}`}>
                  {slot.required ? "Obrigatório" : "Opcional"}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-control border border-tec-border/15 bg-tec-field px-4 py-3 text-sm font-semibold text-white">
            <span className="text-tec-orange">{photo ? 1 : 0}</span> {photo ? "foto anexada" : "fotos anexadas"}
          </div>
        </WizardCard>

        <WizardCard clean>
          <SectionTitle icon={<Camera size={21} />} title="Foto de entrada" />
          <p className="mt-4 text-sm leading-6 text-tec-subtle">
            A foto de entrada é obrigatória e será a imagem de referência da OS.
          </p>
          <label className="mt-4 flex min-h-[230px] cursor-pointer flex-col items-center justify-center rounded-card border border-dashed border-tec-border/15 bg-tec-panel/60 p-5 text-center transition hover:border-tec-orange/60">
            <Upload className="text-tec-orange" size={32} />
            <span className="mt-4 text-base font-bold text-white">Selecionar foto / câmera</span>
            <span className="mt-2 text-sm text-tec-muted">JPG, PNG ou imagem capturada no aparelho</span>
            <input
              accept="image/*"
              capture="environment"
              className="sr-only"
              onChange={(event) => void handleFile(event.currentTarget.files?.[0])}
              type="file"
            />
          </label>
          {isLocalhost ? (
            <Button className="mt-3 w-full" icon={<Camera size={17} />} onClick={() => setPhoto(makeLocalTestPhoto())} variant="secondary">
              Foto teste local
            </Button>
          ) : null}
          <div className="mt-4 rounded-card border border-tec-border/15 bg-tec-field p-4 text-sm text-tec-subtle">
            <span className="font-bold text-white">Dica importante</span>
            <p className="mt-2">Use imagens nítidas e bem iluminadas, sem reflexos ou partes cortadas.</p>
          </div>
        </WizardCard>

        <WizardCard clean>
          <SectionTitle icon={<BadgeCheck size={21} />} title="Prévia" />
          {photo ? (
            <div className="mt-4">
              <img alt="Foto de entrada" className="max-h-[430px] w-full rounded-card object-cover" src={photo.dataUrl} />
              <p className="mt-3 text-xs text-tec-muted">{photo.filename}</p>
            </div>
          ) : (
            <EmptyState
              className="mt-4 min-h-[430px] border-dashed"
              icon={<Camera size={44} />}
              subtitle="A prévia da imagem selecionada será exibida aqui."
              title="Nenhuma foto anexada."
            />
          )}
        </WizardCard>
      </div>
    </div>
  );
}

function SignatureStep({
  customer,
  customerForm,
  device,
  deviceForm,
  photo,
  serviceOrder,
}: {
  customer: CustomerSummary | null;
  customerForm: NewCustomerForm;
  device: CustomerDeviceSummary | null;
  deviceForm: NewDeviceForm;
  photo: { dataUrl: string; filename: string } | null;
  serviceOrder: { reported_defect: string; physical_state: string; accessories_received: string };
}) {
  const customerName = customer?.customer_name ?? customerForm.customer_name;
  const customerPhone = customer?.mobile_no ?? customerForm.mobile_no;
  const customerDocument = customer?.custom_cpf || customer?.custom_rg || customerForm.custom_cpf || customerForm.custom_rg || "Documento não informado";
  const deviceName = device
    ? [device.brand, device.model, device.color].filter(Boolean).join(" ") || device.name
    : [deviceForm.brand, deviceForm.model, deviceForm.color].filter(Boolean).join(" ");
  const deviceImei = device?.imei_serial ?? deviceForm.imei_serial;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <SummaryTile icon={<UserRound size={24} />} label="Cliente" value={customerName || "Cliente"} helper={customerPhone || "Telefone"} />
        <SummaryTile icon={<Smartphone size={24} />} label="Aparelho" value={deviceName || "Aparelho"} helper={device?.capacity ?? deviceForm.capacity} />
        <SummaryTile icon={<Zap size={24} />} label="Defeitos relatados" value={firstSentence(serviceOrder.reported_defect)} helper="Relato automático" tone="orange" />
        <SummaryTile icon={<ShieldCheck size={24} />} label="Estado físico" value={serviceOrder.physical_state || "Não informado"} helper="Declarado" tone="green" />
        <SummaryTile icon={<Camera size={24} />} label="Fotos anexadas" value={photo ? "1 foto" : "0 fotos"} helper={photo?.filename ?? "Foto obrigatória"} tone="green" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.08fr_1fr]">
        <WizardCard clean>
          <SectionTitle icon={<FileText size={21} />} title="Revisão do check-in" />
          <div className="mt-4 divide-y divide-tec-border/15 rounded-card border border-tec-border/15 bg-tec-field">
            <ReviewRow label="Cliente" value={`${customerName || "Cliente"} • ${customerDocument} • ${customerPhone || "Sem telefone"}`} />
            <ReviewRow
              label="Aparelho"
              value={`${deviceName || "Aparelho"}${device?.capacity || deviceForm.capacity ? ` • ${device?.capacity ?? deviceForm.capacity}` : ""} • IMEI / Serial: ${deviceImei}`}
            />
            <ReviewRow label="Relato automático" value={serviceOrder.reported_defect || "Não informado"} />
            <ReviewRow label="Estado físico declarado" value={serviceOrder.physical_state || "Não informado"} />
            <ReviewRow label="Acessórios recebidos" value={serviceOrder.accessories_received || "Sem acessórios informados"} />
            <ReviewRow label="Fotos anexadas" value={photo ? "1 foto de entrada" : "Nenhuma foto anexada"} />
          </div>
        </WizardCard>

        <WizardCard clean>
          <SectionTitle icon={<PenLine size={21} />} title="Aceite por link seguro" />
          <p className="mt-4 text-sm leading-6 text-tec-subtle">
            Crie a OS agora. Em seguida, o balcão gera um QR/link de uso único para o cliente conferir os dados, capturar a selfie ao vivo, assinar e consentir com a LGPD.
          </p>
          <div className="mt-5 rounded-card border border-tec-orange/25 bg-tec-orange/10 p-4 text-sm text-tec-subtle">
            A OS ficará em Entrada criada até o cliente concluir o aceite. O motor continuará bloqueando qualquer avanço técnico sem foto e assinatura.
          </div>
        </WizardCard>
      </div>
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
  onOpenOrder: (response: CheckinResponse) => void;
}) {
  const [acceptance, setAcceptance] = useState<AcceptanceIssueResponse | null>(null);
  const [acceptanceError, setAcceptanceError] = useState<string | null>(null);
  const [exceptionRequestOpen, setExceptionRequestOpen] = useState(false);
  const [exceptionRequestSent, setExceptionRequestSent] = useState<string | null>(null);
  const [issuingAcceptance, setIssuingAcceptance] = useState(true);

  useEffect(() => {
    let active = true;
    setIssuingAcceptance(true);
    setAcceptanceError(null);
    void balcao.issueAcceptance(created.service_order.name, "Entrada")
      .then((result) => active && setAcceptance(result))
      .catch((caught) => active && setAcceptanceError(caught instanceof Error ? caught.message : "Não foi possível gerar o link de aceite."))
      .finally(() => active && setIssuingAcceptance(false));
    return () => {
      active = false;
    };
  }, [created.service_order.name]);

  const copyAcceptanceLink = async () => {
    if (!acceptance) return;
    try {
      await navigator.clipboard.writeText(acceptance.link);
    } catch {
      setAcceptanceError("Não foi possível copiar automaticamente. Use o QR Code ou copie o link exibido no detalhe da OS.");
    }
  };

  const copyTrackingLink = async () => {
    try {
      await navigator.clipboard.writeText(created.tracking.link);
      setAcceptanceError(null);
    } catch {
      setAcceptanceError("Não foi possível copiar automaticamente. Use o QR Code ou copie o link exibido no detalhe da OS.");
    }
  };

  const sendTrackingWhatsApp = () => {
    const text = `Olá! Acompanhe o status do seu reparo Tecponto por este link seguro: ${created.tracking.link}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section className="rounded-card border border-tec-success/30 bg-tec-success/10 p-5">
        <CheckCircle2 className="text-tec-success" size={28} />
        <h3 className="mt-4 text-2xl font-bold text-white">{created.service_order.name}</h3>
        <p className="mt-2 text-sm text-tec-subtle">
          OS criada em Entrada criada com a foto salva. Entregue o QR/link para o cliente concluir o aceite com selfie e assinatura.
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button
            onClick={() => {
              onOpenOrder(created);
            }}
            variant="primary"
          >
            Abrir detalhe da OS
          </Button>
          <Button onClick={onClose}>Fechar</Button>
        </div>
      </section>
      <section className="rounded-card border border-tec-border/15 bg-tec-panel-strong p-4">
        <h3 className="flex items-center gap-2 text-sm font-bold text-white"><QrCode className="text-tec-orange" size={17} /> Aceite de entrada</h3>
        {issuingAcceptance ? <p className="mt-3 text-sm text-tec-muted">Gerando link seguro...</p> : null}
        {acceptance ? (
          <div className="mt-3 space-y-3">
            <div className="mx-auto w-fit rounded-card bg-white p-3"><img alt="QR Code do aceite de entrada" className="h-40 w-40" src={acceptance.qr_svg} /></div>
            <p className="text-xs leading-5 text-tec-muted">Uso único, expira em 24 horas. O cliente só confirma; não pode editar a OS.</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <Button onClick={() => void copyAcceptanceLink()} variant="secondary">Copiar link</Button>
              <Button onClick={() => setExceptionRequestOpen(true)} variant="ghost">Solicitar exceção sem selfie</Button>
            </div>
            {exceptionRequestSent ? <p className="rounded-card border border-tec-success/30 bg-tec-success/10 p-3 text-xs text-tec-success">{exceptionRequestSent}</p> : null}
          </div>
        ) : null}
        {acceptanceError ? <p className="mt-3 rounded-card border border-tec-red/30 bg-tec-red/10 p-3 text-xs text-tec-red">{acceptanceError}</p> : null}
        <div className="mt-5 border-t border-tec-border/15 pt-5">
          <h3 className="flex items-center gap-2 text-sm font-bold text-white"><QrCode className="text-tec-orange" size={17} /> Rastreio do reparo</h3>
          <div className="mt-3 flex items-center gap-3">
            <div className="w-fit rounded-card bg-white p-2"><img alt="QR Code do rastreio do reparo" className="h-20 w-20" src={created.tracking.qr_svg} /></div>
            <p className="text-xs leading-5 text-tec-muted">Este link acompanha o reparo inteiro e permanece disponível por 90 dias após a retirada.</p>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <Button onClick={() => void copyTrackingLink()} variant="secondary">Copiar link de rastreio</Button>
            <Button onClick={sendTrackingWhatsApp} variant="secondary">Enviar por WhatsApp</Button>
          </div>
        </div>
        <h3 className="mt-5 text-sm font-bold text-white">Impressão</h3>
        <div className="mt-3 space-y-2">
          {created.service_order.print_links.map((link) => (
            <a
              className="flex min-h-11 items-center justify-between gap-3 rounded-card border border-tec-border/15 bg-tec-field px-3 text-sm font-semibold text-tec-subtle transition hover:border-tec-orange/50 hover:text-white"
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
      {acceptance ? (
        <ApprovalRequestModal
          approver="Gestor"
          onClose={() => setExceptionRequestOpen(false)}
          onCreated={() => setExceptionRequestSent("Solicitação enviada, aguardando o Gestor.")}
          onToast={(message, tone) => {
            if (tone === "error") setAcceptanceError(message);
          }}
          open={exceptionRequestOpen}
          payload={{}}
          referenceName={acceptance.acceptance}
          requestType="acceptance_selfie_exception"
          title="O cliente não consegue ou não autoriza a selfie. Deseja solicitar ao Gestor a dispensa excepcional da selfie? A assinatura e o consentimento LGPD continuam obrigatórios."
        />
      ) : null}
    </div>
  );
}

function WizardCard({ children, className = "", clean = false }: { children: ReactNode; className?: string; clean?: boolean }) {
  return (
    <section className={`rounded-card border border-tec-border/15 ${clean ? "bg-tec-panel shadow-none" : "bg-[linear-gradient(180deg,rgba(255,255,255,0.035),rgba(255,255,255,0.014))] shadow-[0_18px_42px_rgba(0,0,0,0.22)]"} p-5 ${className}`}>
      {children}
    </section>
  );
}

function MicrostepChoiceCard({
  compact = false,
  icon,
  label,
  onClick,
  text,
}: {
  compact?: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
  text: string;
}) {
  return (
    <button
      className={`group rounded-card border border-tec-border/15 bg-tec-panel text-left transition hover:border-tec-orange/55 hover:bg-tec-orange/10 ${compact ? "min-h-[136px] p-4" : "min-h-[190px] p-6 shadow-[0_18px_42px_rgba(0,0,0,0.18)]"}`}
      onClick={onClick}
      type="button"
    >
      <span className={`${compact ? "h-10 w-10" : "h-14 w-14"} grid place-items-center rounded-control bg-tec-orange/14 text-tec-orange transition group-hover:bg-tec-orange group-hover:text-tec-ink`}>
        {icon}
      </span>
      <span className={`${compact ? "mt-3 text-lg" : "mt-5 text-2xl"} block font-bold text-white`}>{label}</span>
      <span className={`${compact ? "mt-2 leading-5" : "mt-3 leading-6"} block max-w-xl text-sm text-tec-subtle`}>{text}</span>
      <span className={`${compact ? "mt-3" : "mt-5"} inline-flex items-center gap-2 text-sm font-bold text-tec-orange`}>
        Continuar
        <ArrowRight size={17} />
      </span>
    </button>
  );
}

function ChoicePanel({ children, compact = false, label }: { children: ReactNode; compact?: boolean; label: string }) {
  if (compact) {
    return (
      <div>
        <p className="mb-2 text-xs font-bold uppercase tracking-wide text-tec-muted">{label}</p>
        <div className="flex flex-wrap gap-2 [&>button]:!min-h-0 [&>button]:!px-3 [&>button]:!py-2 [&>button]:!text-left [&>button>span]:hidden [&>button>svg]:hidden">
          {children}
        </div>
      </div>
    );
  }

  return (
    <WizardCard className="p-4">
      <p className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
        {label}
        <span className="h-1.5 w-1.5 rounded-full bg-tec-orange" />
      </p>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{children}</div>
    </WizardCard>
  );
}

function ChipGroup({
  children,
  compact = false,
  label,
  multiple,
  required,
}: {
  children: ReactNode;
  compact?: boolean;
  label: string;
  multiple?: boolean;
  required?: boolean;
}) {
  return (
    <div>
      <p className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
        {label}
        {required ? <span className="h-1.5 w-1.5 rounded-full bg-tec-orange" /> : null}
        {multiple ? <span className="text-xs font-medium text-tec-muted">Seleção múltipla</span> : null}
      </p>
      <div className={compact ? "flex flex-wrap gap-2 [&>button]:!min-h-9 [&>button]:!px-3 [&>button]:!text-xs" : "flex flex-wrap gap-2"}>{children}</div>
    </div>
  );
}

function CheckboxGrid({ children, compact = false, label, required }: { children: ReactNode; compact?: boolean; label: string; required?: boolean }) {
  return (
    <div>
      <p className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
        {label}
        {required ? <span className="h-1.5 w-1.5 rounded-full bg-tec-orange" /> : null}
        <span className="text-xs font-medium text-tec-muted">Seleção múltipla</span>
      </p>
      <div className={compact ? "grid gap-2 sm:grid-cols-2 xl:grid-cols-3 [&>button]:!min-h-0 [&>button]:!p-2" : "grid gap-3 sm:grid-cols-2 xl:grid-cols-3"}>{children}</div>
    </div>
  );
}

function OptionCard({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={`relative min-h-24 rounded-card border px-3 py-4 text-center text-sm font-bold transition ${
        active
          ? "border-tec-orange bg-tec-orange/12 text-white shadow-[0_0_0_1px_rgba(254,80,0,0.22)]"
          : "border-tec-border/15 bg-tec-field text-tec-subtle hover:border-tec-orange/50 hover:text-white"
      }`}
      onClick={onClick}
      type="button"
    >
      <span className={`mx-auto mb-3 grid h-9 w-9 place-items-center rounded-control ${active ? "bg-tec-orange/20 text-tec-orange" : "bg-tec-field/65 text-tec-muted"}`}>{icon}</span>
      {label}
      {active ? <Check className="absolute right-3 top-3 text-tec-orange" size={17} /> : null}
    </button>
  );
}

function OptionChip({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean;
  icon?: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={`inline-flex min-h-11 items-center gap-2 rounded-control border px-4 text-sm font-semibold transition ${
        active
          ? "border-tec-orange bg-tec-orange/12 text-white shadow-[0_0_0_1px_rgba(254,80,0,0.2)]"
          : "border-tec-border/15 bg-tec-field text-tec-subtle hover:border-tec-orange/50 hover:text-white"
      }`}
      onClick={onClick}
      type="button"
    >
      {icon ? <span className={active ? "text-tec-orange" : "text-tec-muted"}>{icon}</span> : null}
      {label}
      {active ? <CheckCircle2 className="text-tec-orange" size={16} /> : null}
    </button>
  );
}

function ColorChip({
  active,
  color,
  onClick,
}: {
  active: boolean;
  color: string;
  onClick: () => void;
}) {
  const colorMap: Record<string, string> = {
    Azul: "bg-tec-blue",
    Branco: "bg-white",
    Dourado: "bg-tec-amber",
    Prata: "bg-zinc-300",
    Preto: "bg-black",
    Rosa: "bg-pink-400",
  };
  return (
    <OptionChip
      active={active}
      icon={<span className={`block h-4 w-4 rounded-full border border-tec-border/25 ${colorMap[color] ?? "bg-tec-field"}`} />}
      label={color}
      onClick={onClick}
    />
  );
}

function CheckboxOption({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button className="flex items-center gap-3 text-left text-sm text-tec-subtle" onClick={onClick} type="button">
      <span
        className={`grid h-5 w-5 shrink-0 place-items-center rounded border ${
          active ? "border-tec-orange bg-tec-orange text-tec-ink" : "border-tec-border/25 bg-tec-field"
        }`}
      >
        {active ? <Check size={14} /> : null}
      </span>
      <span className={active ? "font-semibold text-white" : undefined}>{label}</span>
    </button>
  );
}

function InfoBanner({ icon = <Info size={26} />, text, title }: { icon?: ReactNode; text: string; title: string }) {
  return (
    <div className="flex gap-4 rounded-card border border-tec-blue/25 bg-tec-blue/10 p-4">
      <span className="mt-1 text-tec-blue">{icon}</span>
      <div>
        <p className="font-bold text-tec-blue">{title}</p>
        <p className="mt-1 text-sm text-tec-subtle">{text}</p>
      </div>
    </div>
  );
}

function EmptyState({
  className = "",
  icon,
  subtitle,
  title,
}: {
  className?: string;
  icon: ReactNode;
  subtitle: string;
  title: string;
}) {
  return (
    <div className={`grid min-h-[240px] place-items-center rounded-card border border-tec-border/15 bg-tec-panel/30 p-5 text-center ${className}`}>
      <div>
        <span className="mx-auto grid h-16 w-16 place-items-center rounded-full border border-tec-border/15 bg-tec-field text-tec-muted">{icon}</span>
        <p className="mt-5 font-semibold text-tec-subtle">{title}</p>
        <p className="mx-auto mt-2 max-w-xs text-sm leading-6 text-tec-muted">{subtitle}</p>
      </div>
    </div>
  );
}

function SummaryTile({
  helper,
  icon,
  label,
  tone = "default",
  value,
}: {
  helper?: string;
  icon: ReactNode;
  label: string;
  tone?: "default" | "green" | "orange";
  value: string;
}) {
  const toneClass =
    tone === "green"
      ? "bg-tec-success/10 text-tec-success"
      : tone === "orange"
        ? "bg-tec-orange/12 text-tec-orange"
        : "bg-tec-blue/10 text-tec-blue";
  return (
    <div className="rounded-card border border-tec-border/15 bg-tec-panel-strong p-4">
      <div className="flex items-start gap-3">
        <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-control ${toneClass}`}>{icon}</span>
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase text-tec-muted">{label}</p>
          <p className="mt-1 line-clamp-2 font-bold text-white">{value}</p>
          {helper ? <p className="mt-1 line-clamp-1 text-xs text-tec-muted">{helper}</p> : null}
        </div>
      </div>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-2 p-4 text-sm md:grid-cols-[190px_minmax(0,1fr)]">
      <dt className="font-bold text-tec-subtle">{label}</dt>
      <dd className="leading-6 text-white">{value}</dd>
    </div>
  );
}

function SectionTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-10 w-10 place-items-center rounded-card bg-tec-orange/15 text-tec-orange">{icon}</span>
      <h3 className="text-lg font-bold text-white">{title}</h3>
    </div>
  );
}

function Badge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-control border border-tec-border/15 bg-tec-field px-3 py-2 text-xs font-bold text-tec-subtle">
      <span className="h-2 w-2 rounded-full bg-tec-orange" />
      {children}
    </span>
  );
}

function SelectedBox({ lines, onClear }: { lines: string[]; onClear: () => void }) {
  return (
    <div className="mt-4 rounded-card border border-tec-orange/35 bg-tec-orange/10 p-4">
      {lines.map((line) => (
        <p className="text-sm text-tec-subtle first:font-bold first:text-white" key={line}>
          {line}
        </p>
      ))}
      <Button className="mt-4" icon={<X size={17} />} onClick={onClear}>
        Trocar
      </Button>
    </div>
  );
}

function Field({
  autoComplete,
  highlight = false,
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
  highlight?: boolean;
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
      <span className="mb-2 flex items-center justify-between gap-2 text-sm font-semibold text-white">
        <span>{label}</span>
        <span className={required ? "text-xs font-bold uppercase text-tec-orange" : "text-xs font-semibold uppercase text-tec-muted"}>{required ? "Obrigatório" : "Opcional"}</span>
      </span>
      <input
        aria-required={required || undefined}
        autoComplete={autoComplete}
        className={`h-12 w-full rounded-control border bg-tec-field px-4 text-sm text-white outline-none placeholder:text-tec-muted focus:border-tec-orange/70 ${highlight ? "border-tec-orange/55 shadow-[0_0_0_1px_rgba(254,80,0,0.12)]" : "border-tec-border/15"}`}
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
  maxLength,
  onChange,
  placeholder,
  required,
  value,
}: {
  label: string;
  maxLength?: number;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  value: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 flex items-center justify-between gap-2 text-sm font-semibold text-white">
        <span>
          {label}
          {required ? <span className="ml-2 text-tec-orange">•</span> : null}
        </span>
        <span className={required ? "text-xs font-bold uppercase text-tec-orange" : "text-xs font-semibold uppercase text-tec-muted"}>{required ? "Obrigatório" : "Opcional"}</span>
      </span>
      <textarea
        aria-required={required || undefined}
        className="min-h-[86px] w-full resize-none rounded-control border border-tec-border/15 bg-tec-field p-4 text-sm text-white outline-none placeholder:text-tec-muted focus:border-tec-orange/70"
        maxLength={maxLength}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
        value={value}
      />
      {maxLength ? <span className="mt-1 block text-right text-xs text-tec-muted">{value.length}/{maxLength}</span> : null}
    </label>
  );
}

function buildServiceSummary(selections: ServiceSelections) {
  const parts: string[] = [];
  if (selections.defects.length) {
    const locations = selections.problemLocations.length ? ` (${joinPt(selections.problemLocations)})` : "";
    parts.push(`Cliente relata ${joinPt(selections.defects).toLowerCase()}${locations}.`);
  }
  if (selections.physicalStates.length) {
    parts.push(`Estado físico declarado: ${joinPt(selections.physicalStates).toLowerCase()}.`);
  }
  if (selections.accessories.length) {
    parts.push(`Acessórios recebidos: ${joinPt(selections.accessories).toLowerCase()}.`);
  }
  if (selections.observations.trim()) {
    parts.push(`Observações adicionais: ${selections.observations.trim()}`);
  }
  return parts.join(" ");
}

function joinPt(values: string[]) {
  if (values.length <= 1) {
    return values[0] ?? "";
  }
  return `${values.slice(0, -1).join(", ")} e ${values[values.length - 1]}`;
}

function firstSentence(value: string) {
  const [first] = value.split(".");
  return first || "Não informado";
}

function formatShortDate(value: string) {
  if (!value) {
    return "data n\u00e3o informada";
  }
  const normalized = value.includes("T") ? value : `${value}T12:00:00`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("pt-BR");
}

function defectIcon(defect: string) {
  if (defect.includes("Bateria") || defect.includes("carrega") || defect.includes("Conector")) {
    return <Battery size={16} />;
  }
  if (defect.includes("Microfone")) {
    return <Mic size={16} />;
  }
  if (defect.includes("Tela")) {
    return <Monitor size={16} />;
  }
  if (defect.includes("áudio")) {
    return <Headphones size={16} />;
  }
  return <Zap size={16} />;
}

function locationIcon(location: string) {
  if (location === "Bateria") {
    return <Battery size={16} />;
  }
  if (location === "Tela") {
    return <Monitor size={16} />;
  }
  if (location === "Microfone") {
    return <Mic size={16} />;
  }
  if (location === "Câmera") {
    return <Camera size={16} />;
  }
  if (location === "Alto-falante") {
    return <Headphones size={16} />;
  }
  return <Smartphone size={16} />;
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
    context.strokeStyle = "rgba(255,255,255,0.25)";
    context.lineWidth = 4;
    context.strokeRect(32, 230, 420, 240);
    context.fillText("Aparelho fotografado no balcão", 64, 360);
  }
  return {
    dataUrl: canvas.toDataURL("image/png"),
    filename: "foto-entrada-teste-local.png",
  };
}
