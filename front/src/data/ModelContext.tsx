/**
 * Глобальный контекст выбранной модели.
 *
 * Все страницы приложения фильтруют данные по modelVersion из этого контекста.
 * При смене модели в Layout-хедере обновляется контекст → страницы автоматически
 * перезапрашивают данные с новым model_version.
 */
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { fetchModels, activateModel as apiActivateModel, type ModelInfo } from "./api";

interface ModelContextType {
  /** Текущая выбранная версия модели (null = нет модели) */
  modelVersion: string | null;
  /** Все доступные модели */
  models: ModelInfo[];
  /** Загрузка списка моделей */
  loading: boolean;
  /** Переключить модель (активировать на бэкенде + обновить контекст) */
  switchModel: (version: string) => Promise<void>;
  /** Перезагрузить список моделей */
  refreshModels: () => Promise<void>;
}

const ModelContext = createContext<ModelContextType | null>(null);

export function ModelProvider({ children }: { children: ReactNode }) {
  const [modelVersion, setModelVersion] = useState<string | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const refreshModels = useCallback(async () => {
    try {
      const res = await fetchModels();
      setModels(res.models);
      // Если нет выбранной модели — ставим активную
      const active = res.models.find((m) => m.is_active);
      setModelVersion((prev) => {
        // Если выбранная модель всё ещё существует — оставляем
        if (prev && res.models.some((m) => m.version === prev)) return prev;
        return active?.version ?? null;
      });
    } catch {
      // silent
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    refreshModels();
  }, [refreshModels]);

  const switchModel = useCallback(async (version: string) => {
    await apiActivateModel(version);
    setModels((prev) =>
      prev.map((m) => ({ ...m, is_active: m.version === version ? 1 : 0 }))
    );
    setModelVersion(version);
  }, []);

  return (
    <ModelContext.Provider value={{ modelVersion, models, loading, switchModel, refreshModels }}>
      {children}
    </ModelContext.Provider>
  );
}

export function useModel() {
  const ctx = useContext(ModelContext);
  if (!ctx) throw new Error("useModel must be inside ModelProvider");
  return ctx;
}

