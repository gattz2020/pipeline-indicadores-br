// Configuração Global do Chart.js para Dark Theme
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.scale.grid.color = 'rgba(255, 255, 255, 0.05)';
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(10, 16, 32, 0.9)';
Chart.defaults.plugins.tooltip.titleFont = { family: "'Outfit', sans-serif", size: 14 };
Chart.defaults.plugins.tooltip.padding = 12;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.1)';
Chart.defaults.plugins.tooltip.borderWidth = 1;

let dashboardData = [];
let charts = {};

// Cores
const colors = {
    selic: '#34d399', // primary
    ipca: '#06b6d4',  // secondary
    dolar: '#f59e0b', // accent
    igpm: '#f43f5e'   // danger
};

// Formatação de números
const formatPercent = (val) => val != null ? `${val.toFixed(2).replace('.', ',')}%` : '--';
const formatCurrency = (val) => val != null ? `R$ ${val.toFixed(2).replace('.', ',')}` : '--';
const parseDate = (dateStr) => {
    const [year, month] = dateStr.split('-');
    const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    return `${months[parseInt(month)-1]}/${year.substring(2)}`;
};

async function loadData() {
    try {
        const res = await fetch('data/indicadores.json');
        if (!res.ok) throw new Error('Falha ao carregar dados');
        
        const payload = await res.json();
        dashboardData = payload.history;
        
        // Atualiza Header
        const dateObj = new Date(payload.generated_at);
        document.getElementById('last-update').textContent = `Atualizado em: ${dateObj.toLocaleString('pt-BR')}`;
        
        // Atualiza KPIs
        document.getElementById('kpi-selic').textContent = formatPercent(payload.latest_kpis.selic_meta_fim);
        document.getElementById('kpi-ipca').textContent = formatPercent(payload.latest_kpis.ipca_12m);
        document.getElementById('kpi-juros').textContent = formatPercent(payload.latest_kpis.juros_real_ex_post);
        document.getElementById('kpi-dolar').textContent = formatCurrency(payload.latest_kpis.dolar_fim);
        
        // Renderiza Gráficos (padrão 12 meses)
        renderCharts(12);
        
    } catch (err) {
        console.error(err);
        document.getElementById('last-update').textContent = 'Erro ao carregar dados. Verifique o console.';
    }
}

function filterData(months) {
    if (months === 0) return dashboardData;
    return dashboardData.slice(-months);
}

function renderCharts(months) {
    const data = filterData(months);
    const labels = data.map(d => parseDate(d.mes));
    
    // Gráfico 1: Selic x IPCA
    createOrUpdateChart('chartSelicIpca', {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Selic Meta',
                    data: data.map(d => d.selic_meta_fim),
                    borderColor: colors.selic,
                    backgroundColor: colors.selic,
                    borderWidth: 2,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHitRadius: 10
                },
                {
                    label: 'IPCA 12m',
                    data: data.map(d => d.ipca_12m),
                    borderColor: colors.ipca,
                    backgroundColor: colors.ipca,
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.3,
                    pointRadius: 0,
                    pointHitRadius: 10
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: { y: { ticks: { callback: (v) => v + '%' } } }
        }
    });
    
    // Gráfico 2: Dólar
    createOrUpdateChart('chartDolar', {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Dólar (Média Mensal)',
                data: data.map(d => d.dolar_medio),
                borderColor: colors.dolar,
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHitRadius: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { display: false } },
            scales: { y: { ticks: { callback: (v) => 'R$ ' + v.toFixed(2) } } }
        }
    });
    
    // Gráfico 3: IPCA vs IGPM Mensal
    createOrUpdateChart('chartInflacaoMensal', {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'IPCA Mês',
                    data: data.map(d => d.ipca_mensal),
                    backgroundColor: colors.ipca,
                    borderRadius: 4
                },
                {
                    label: 'IGP-M Mês',
                    data: data.map(d => d.igpm_mensal),
                    backgroundColor: colors.igpm,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: { y: { ticks: { callback: (v) => v + '%' } } }
        }
    });
}

function createOrUpdateChart(id, config) {
    const ctx = document.getElementById(id).getContext('2d');
    if (charts[id]) {
        charts[id].data = config.data;
        charts[id].update();
    } else {
        charts[id] = new Chart(ctx, config);
    }
}

// Event Listeners para botões de filtro
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('is-active'));
        e.target.classList.add('is-active');
        const months = parseInt(e.target.getAttribute('data-months'));
        renderCharts(months);
    });
});

// Inicialização
document.addEventListener('DOMContentLoaded', loadData);
