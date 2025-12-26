// Main JavaScript for Sistema Financeiro

// Formatação de valores monetários
function formatarMoeda(valor) {
    return valor.toFixed(2).replace('.', ',');
}

// Validar formulários
document.addEventListener('DOMContentLoaded', function () {
    // Auto-close alerts após 5 segundos
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Confirmar exclusões
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            if (!confirm('Tem certeza que deseja excluir este item?')) {
                e.preventDefault();
            }
        });
    });

    // Formatar inputs de valor
    const valorInputs = document.querySelectorAll('input[name="valor"]');
    valorInputs.forEach(input => {
        input.addEventListener('blur', function () {
            let valor = this.value.replace(',', '.');
            if (!isNaN(valor) && valor !== '') {
                this.value = parseFloat(valor).toFixed(2).replace('.', ',');
            }
        });

        // Aceitar apenas números, vírgula e ponto
        input.addEventListener('keypress', function (e) {
            const char = String.fromCharCode(e.which);
            if (!/[\d.,]/.test(char)) {
                e.preventDefault();
            }
        });
    });
});

// Função para atualizar gráficos com dados da API
async function carregarGrafico(endpoint, canvasId, tipo = 'bar') {
    try {
        const response = await fetch(endpoint);
        const data = await response.json();

        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        new Chart(ctx, {
            type: tipo,
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Valor (R$)',
                    data: data.values || data.despesas,
                    backgroundColor: tipo === 'pie'
                        ? generateColors(data.labels.length)
                        : 'rgba(76, 175, 80, 0.6)',
                    borderColor: 'rgba(76, 175, 80, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: tipo === 'pie'
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += 'R$ ' + context.parsed.y.toFixed(2).replace('.', ',');
                                return label;
                            }
                        }
                    }
                },
                scales: tipo !== 'pie' ? {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return 'R$ ' + value.toFixed(2).replace('.', ',');
                            }
                        }
                    }
                } : {}
            }
        });
    } catch (error) {
        console.error('Erro ao carregar gráfico:', error);
    }
}

// Gerar cores para gráficos
function generateColors(count) {
    const colors = [
        'rgba(76, 175, 80, 0.6)',   // Verde
        'rgba(33, 150, 243, 0.6)',   // Azul
        'rgba(255, 152, 0, 0.6)',    // Laranja
        'rgba(156, 39, 176, 0.6)',   // Roxo
        'rgba(244, 67, 54, 0.6)',    // Vermelho
        'rgba(0, 188, 212, 0.6)',    // Ciano
        'rgba(255, 235, 59, 0.6)',   // Amarelo
        'rgba(121, 85, 72, 0.6)',    // Marrom
        'rgba(158, 158, 158, 0.6)',  // Cinza
        'rgba(255, 87, 34, 0.6)'     // Deep Orange
    ];

    const result = [];
    for (let i = 0; i < count; i++) {
        result.push(colors[i % colors.length]);
    }
    return result;
}

// Exportar para uso global
window.carregarGrafico = carregarGrafico;
window.formatarMoeda = formatarMoeda;
