import {
  AlertTriangle,
  Archive,
  Banknote,
  CheckCircle2,
  Clock3,
  Globe2,
  PackageCheck,
  PackageSearch,
  PackageX,
  PowerOff,
  SearchCheck,
  ShoppingBag,
  ShoppingCart,
  Tags,
  UserPlus,
  UserRoundCheck,
  UsersRound,
  Wrench,
  type LucideIcon,
} from "lucide-react";

import type { StatBarItem } from "./StatBar";

type Visual = Pick<StatBarItem, "icon" | "tone">;

function visual(Icon: LucideIcon, tone: NonNullable<StatBarItem["tone"]>): Visual {
  return { icon: <Icon size={19} />, tone };
}

export function getStatBarVisual(scope: string, key: string): Visual {
  const maps: Record<string, Record<string, Visual>> = {
    service_orders: {
	  overdue: visual(AlertTriangle, "orange"),
      "Entrada criada": visual(Archive, "blue"),
      "Em diagnóstico": visual(SearchCheck, "blue"),
      "Aguardando aprovação": visual(Clock3, "amber"),
      "Aguardando peça": visual(PackageSearch, "blue"),
      "Em reparo": visual(Wrench, "orange"),
      "Pronto para retirada": visual(ShoppingBag, "green"),
    },
    customers: {
      active: visual(UserRoundCheck, "green"),
      all: visual(UsersRound, "blue"),
      new: visual(UserPlus, "orange"),
    },
    stock: {
      all: visual(PackageCheck, "blue"),
      low: visual(AlertTriangle, "amber"),
      empty: visual(PackageX, "orange"),
    },
    trades: {
      open: visual(Clock3, "blue"),
      approval: visual(CheckCircle2, "amber"),
      closed: visual(Archive, "green"),
    },
    sales: {
      today: visual(ShoppingCart, "green"),
      amount: visual(Banknote, "orange"),
    },
    catalog: {
      active: visual(Wrench, "green"),
      all: visual(Tags, "blue"),
      categories: visual(Archive, "orange"),
    },
    "product-categories": {
      active: visual(Tags, "green"),
      online: visual(Globe2, "blue"),
      internal: visual(PackageSearch, "amber"),
      inactive: visual(PowerOff, "orange"),
    },
  };
  return maps[scope]?.[key] ?? visual(Archive, "blue");
}
