import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Dataset } from '@/types'

export const useDatasetStore = defineStore('datasets', () => {
  const datasets = ref<Dataset[]>([])
  const currentDataset = ref<Dataset | null>(null)
  const isLoading = ref(false)

  function setDatasets(newDatasets: Dataset[]) {
    datasets.value = newDatasets
  }

  function setCurrentDataset(dataset: Dataset | null) {
    currentDataset.value = dataset
  }

  function addDataset(dataset: Dataset) {
    datasets.value.unshift(dataset)
  }

  function updateDataset(updated: Dataset) {
    const index = datasets.value.findIndex(d => d.id === updated.id)
    if (index !== -1) {
      datasets.value[index] = updated
    }
  }

  function removeDataset(id: string) {
    datasets.value = datasets.value.filter(d => d.id !== id)
  }

  return {
    datasets,
    currentDataset,
    isLoading,
    setDatasets,
    setCurrentDataset,
    addDataset,
    updateDataset,
    removeDataset
  }
})
