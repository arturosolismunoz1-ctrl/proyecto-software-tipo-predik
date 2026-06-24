import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import type { PreviewData } from '../api/client'

const COLOR_MAP: Record<string, string> = {
  red:    '#ef4444',
  green:  '#22c55e',
  blue:   '#3b82f6',
  yellow: '#eab308',
  orange: '#f97316',
  purple: '#a855f7',
  cyan:   '#06b6d4',
  pink:   '#ec4899',
}

interface Props {
  data: PreviewData | null
  visibleCapas?: Record<string, boolean>
}

export function ResultsOverlay({ data, visibleCapas }: Props) {
  const map = useMap()
  const layersRef = useRef<L.Layer[]>([])

  useEffect(() => {
    // Limpiar capas previas
    layersRef.current.forEach(l => map.removeLayer(l))
    layersRef.current = []

    if (!data) return


    const allLayers: L.Layer[] = []

    // ── Polígonos de zonas (AGEBs o H3) ──────────────────────────────────────
    data.zonas.forEach(feature => {
      const props = feature.properties
      const fillColor = props.hex_color || '#888888'
      const opacity = 0.55 + (props.intensidad || 0) * 0.3

      const layer = L.geoJSON(feature as any, {
        style: {
          color: '#1a1a2e',
          weight: 0.8,
          fillColor,
          fillOpacity: opacity,
        },
      })

      const popupLines: string[] = [
        `<b style="font-size:13px">${props.label || 'Zona'}</b>`,
        `Establecimientos: <b>${props.cantidad}</b>`,
      ]
      if (props.cvegeo) {
        popupLines.push(`AGEB: <code>${props.cvegeo}</code>`)
        if (props.nom_mun) popupLines.push(`Municipio: ${props.nom_mun}`)
        if (props.pobtot) popupLines.push(`Población: ${props.pobtot.toLocaleString()}`)
        if (props.graproes !== undefined)
          popupLines.push(`Escolaridad prom.: ${props.graproes} años`)
      } else if (props.h3_index) {
        popupLines.push(`H3: <code>${props.h3_index}</code>`)
      }

      layer.bindPopup(popupLines.join('<br/>'), { maxWidth: 240 })
      layer.addTo(map)
      allLayers.push(layer)
    })

    // ── Puntos de establecimientos ────────────────────────────────────────────
    data.capas.forEach(capa => {
      if (visibleCapas && visibleCapas[capa.keyword] === false) return
      const markerColor = COLOR_MAP[capa.color] || '#3b82f6'
      const radius = capa.icon === 'star' ? 8 : 6

      capa.puntos.forEach(punto => {
        const marker = L.circleMarker([punto.lat, punto.lon], {
          radius,
          fillColor: markerColor,
          color: '#ffffff',
          weight: 1.5,
          fillOpacity: 0.92,
        })

        marker.bindPopup(
          [
            `<b style="font-size:13px">${punto.nombre || capa.label}</b>`,
            `<span style="color:${markerColor}">■</span> ${capa.label}`,
            punto.clase_actividad ? `Actividad: ${punto.clase_actividad}` : '',
            punto.colonia ? `Col. ${punto.colonia}` : '',
            punto.municipio ? punto.municipio : '',
          ].filter(Boolean).join('<br/>'),
          { maxWidth: 220 }
        )

        marker.addTo(map)
        allLayers.push(marker)
      })
    })

    layersRef.current = allLayers

    // Ajustar vista al resultado
    if (allLayers.length > 0) {
      try {
        const group = L.featureGroup(allLayers)
        const bounds = group.getBounds()
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [30, 30], maxZoom: 14 })
        }
      } catch (_) {}
    }

    return () => {
      layersRef.current.forEach(l => map.removeLayer(l))
      layersRef.current = []
    }
  }, [data, map, visibleCapas])

  return null
}
