#!/bin/bash
# Script para listar y seleccionar el config de VPN correcto

SERVER="root@134.209.37.219"

echo "🔍 Buscando archivos .ovpn en el servidor..."
echo ""

ssh ${SERVER} bash <<'ENDSSH'
echo "📂 Archivos .ovpn encontrados:"
echo "════════════════════════════════════════════════════════"
find /root -name "*.ovpn" -type f 2>/dev/null | while read file; do
    echo ""
    echo "📄 Archivo: $file"
    echo "   Tamaño: $(du -h "$file" | cut -f1)"
    
    # Buscar palabras clave que indiquen ubicación
    if grep -qi "colombia\|bogota\|co\|south.*america" "$file" 2>/dev/null; then
        echo "   ✅ POSIBLE COLOMBIA - Contiene: $(grep -i "colombia\|bogota\|co\|south.*america" "$file" | head -1)"
    fi
    
    # Mostrar remote line para ver IP/hostname del servidor
    remote_line=$(grep "^remote " "$file" 2>/dev/null | head -1)
    if [ -n "$remote_line" ]; then
        echo "   Servidor: $remote_line"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════"
echo ""
echo "📊 Total encontrados: $(find /root -name "*.ovpn" -type f 2>/dev/null | wc -l)"
ENDSSH

echo ""
echo "💡 Revisa la lista arriba y busca el archivo de Colombia"
echo "   Puede llamarse: co.ovpn, colombia.ovpn, south-america.ovpn, etc."
