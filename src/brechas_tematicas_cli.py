import pandas as pd


def construir_reporte_brechas(resumen, comparacion):
    columnas = [
        "comunidad_usuarios",
        "documentos_usuarios",
        "porcentaje_usuarios",
        "tono_usuarios",
        "terminos_usuarios",
        "ejemplo_usuarios",
        "presencia_dmo_misma_comunidad",
        "documentos_dmo_misma_comunidad",
        "comunidad_dmo_mas_cercana",
        "similitud_coseno",
        "terminos_dmo_cercana",
        "relacion_estructural",
        "estado_interpretacion"
    ]

    if resumen.empty:
        return pd.DataFrame(columns=columnas)

    dmo = resumen.loc[resumen["segmento"].eq("DMO")].set_index("comunidad")
    usuarios = resumen.loc[resumen["segmento"].eq("Usuarios")]

    mejores = pd.DataFrame()

    if not comparacion.empty:
        mejores = comparacion.sort_values(
            ["comunidad_usuarios", "similitud_coseno"],
            ascending=[True, False]
        ).drop_duplicates("comunidad_usuarios").set_index("comunidad_usuarios")

    filas = []

    for _, usuario in usuarios.iterrows():
        comunidad = int(usuario["comunidad"])
        compartida = comunidad in dmo.index

        documentos_dmo = int(dmo.loc[comunidad, "documentos"]) if compartida else 0
        cercana = None
        similitud = None

        if comunidad in mejores.index:
            pareja = mejores.loc[comunidad]
            cercana = int(pareja["comunidad_dmo"])
            similitud = float(pareja["similitud_coseno"])

        filas.append({
            "comunidad_usuarios": comunidad,
            "documentos_usuarios": int(usuario["documentos"]),
            "porcentaje_usuarios": usuario["porcentaje_segmento"],
            "tono_usuarios": usuario["tono_predominante"],
            "terminos_usuarios": usuario["terminos"],
            "ejemplo_usuarios": usuario["ejemplo_lexico"],
            "presencia_dmo_misma_comunidad": compartida,
            "documentos_dmo_misma_comunidad": documentos_dmo,
            "comunidad_dmo_mas_cercana": cercana,
            "similitud_coseno": similitud,
            "terminos_dmo_cercana": dmo.loc[cercana, "terminos"] if cercana in dmo.index else "",
            "relacion_estructural": "Comunidad compartida" if compartida else "Solo usuarios",
            "estado_interpretacion": (
                "Requiere validar coincidencia tematica" if compartida
                else "Posible brecha; verificar pertinencia al destino"
            )
        })

    return pd.DataFrame(filas, columns=columnas)


def comparar_presencia_tematica(resumen):
    campos = [
        "documentos",
        "porcentaje_segmento",
        "terminos",
        "tono_predominante",
        "ejemplo_lexico"
    ]

    universos = [("DMO", "dmo"), ("Usuarios", "usuarios")]
    filas = []

    for comunidad, grupo in resumen.groupby("comunidad"):
        fila = {"comunidad": comunidad}

        for universo, sufijo in universos:
            segmento = grupo.loc[grupo["segmento"].eq(universo)]

            for campo in campos:
                predeterminado = 0 if campo in campos[:2] else ""
                fila[f"{campo}_{sufijo}"] = (
                    segmento.iloc[0][campo] if not segmento.empty else predeterminado
                )

        fila["diferencia_pp_usuarios_menos_dmo"] = (
            fila["porcentaje_segmento_usuarios"] - fila["porcentaje_segmento_dmo"]
        )

        if fila["documentos_dmo"] and fila["documentos_usuarios"]:
            fila["relacion"] = "Compartida"
        elif fila["documentos_dmo"]:
            fila["relacion"] = "Solo DMO"
        else:
            fila["relacion"] = "Solo usuarios"

        filas.append(fila)

    columnas = ["comunidad"] + [
        f"{campo}_{sufijo}"
        for _, sufijo in universos
        for campo in campos
    ] + ["diferencia_pp_usuarios_menos_dmo", "relacion"]

    return pd.DataFrame(filas, columns=columnas)
