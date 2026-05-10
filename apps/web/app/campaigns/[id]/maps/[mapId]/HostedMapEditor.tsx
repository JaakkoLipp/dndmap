"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";

import { MapEditor } from "../../../../../components/MapEditor";
import {
  api,
  queryKeys,
  type CampaignMapSnapshot,
  type MapImageState,
  type MapLayer
} from "../../../../../lib/api";
import {
  annotationToEditorObject,
  editorObjectToPayload
} from "../../../../../lib/editorMapping";

type HostedMapEditorProps = {
  campaignId: string;
  mapId: string;
};

function imageFromMap(map: Awaited<ReturnType<typeof api.maps.get>> | undefined) {
  if (!map?.image_url) {
    return null;
  }

  return {
    name: map.image_name ?? map.name,
    src: map.image_url,
    width: map.width,
    height: map.height
  } satisfies MapImageState;
}

function findAnnotationLayer(layers: MapLayer[]) {
  return (
    layers.find((layer) => layer.kind === "objects" && layer.name === "Annotations") ??
    layers.find((layer) => layer.kind === "objects") ??
    null
  );
}

export function HostedMapEditor({ campaignId, mapId }: HostedMapEditorProps) {
  const queryClient = useQueryClient();
  const mapQuery = useQuery({
    queryKey: queryKeys.map(mapId),
    queryFn: () => api.maps.get(mapId)
  });
  const layersQuery = useQuery({
    queryKey: queryKeys.mapLayers(mapId),
    queryFn: () => api.layers.list(mapId)
  });
  const objectsQuery = useQuery({
    queryKey: queryKeys.mapObjects(mapId),
    queryFn: () => api.objects.list(mapId)
  });

  const uploadImage = useMutation({
    mutationFn: (file: File) => api.maps.uploadImage(mapId, file),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.map(mapId) });
    }
  });

  const saveMap = useMutation({
    mutationFn: async (snapshot: CampaignMapSnapshot) => {
      const currentLayers = layersQuery.data ?? [];
      let layer = findAnnotationLayer(currentLayers);

      if (!layer) {
        layer = await api.layers.create(mapId, {
          name: "Annotations",
          kind: "objects",
          visible: true,
          audience: "all",
          sort_order: 0
        });
      }

      await api.maps.update(mapId, {
        name: snapshot.title,
        width: snapshot.image?.width ?? 1600,
        height: snapshot.image?.height ?? 1000
      });

      const existing = new Map((objectsQuery.data ?? []).map((object) => [object.id, object]));
      const nextIds = new Set(snapshot.objects.map((object) => object.id));

      await Promise.all(
        snapshot.objects.map((object) => {
          const payload = editorObjectToPayload(object);
          if (existing.has(object.id)) {
            return api.objects.update(object.id, payload);
          }

          return api.objects.create(mapId, {
            layer_id: layer.id,
            ...payload
          });
        })
      );

      await Promise.all(
        [...existing.keys()]
          .filter((id) => !nextIds.has(id))
          .map((id) => api.objects.delete(id))
      );
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.map(mapId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.mapLayers(mapId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.mapObjects(mapId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.campaignMaps(campaignId) })
      ]);
    }
  });

  const editorObjects = useMemo(
    () =>
      (objectsQuery.data ?? [])
        .map(annotationToEditorObject)
        .filter((object) => object !== null),
    [objectsQuery.data]
  );
  const editorImage = useMemo(() => imageFromMap(mapQuery.data), [mapQuery.data]);

  if (mapQuery.isLoading || layersQuery.isLoading || objectsQuery.isLoading) {
    return <main className="app-shell centered-shell">Loading map…</main>;
  }

  if (mapQuery.error || layersQuery.error || objectsQuery.error) {
    const error = mapQuery.error ?? layersQuery.error ?? objectsQuery.error;
    return (
      <main className="app-shell centered-shell">
        {error instanceof Error ? error.message : "Map could not be loaded"}
      </main>
    );
  }

  return (
    <MapEditor
      initialImage={editorImage}
      initialObjects={editorObjects}
      initialTitle={mapQuery.data?.name ?? "Campaign Map"}
      onSave={(snapshot) => saveMap.mutateAsync(snapshot)}
      onUploadImage={async (file) => {
        await uploadImage.mutateAsync(file);
      }}
      saveLabel={saveMap.isPending ? "Saving" : "Save"}
    />
  );
}
