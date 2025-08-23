<template>
  <v-dialog v-model="dialog" max-width="1200" persistent scrollable>
    <v-card>
      <!-- Header -->
      <v-card-title class="bg-primary white--text">
        <v-icon left color="white">mdi-history</v-icon>
        {{ __("Previous Transactions") }}
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" variant="text" color="white" @click="close_dialog">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <!-- Filters Section -->
      <v-card-text class="pa-4">
        <v-row dense>
          <!-- Date Range Filters -->
          <v-col cols="12" md="3">
            <v-menu v-model="from_date_menu" :close-on-content-click="false" transition="scale-transition">
              <template v-slot:activator="{ props }">
                <v-text-field
                  :model-value="formatDateDisplay(from_date)"
                  :label="__('From Date')"
                  prepend-inner-icon="mdi-calendar"
                  variant="outlined"
                  density="compact"
                  readonly
                  v-bind="props"
                  clearable
                  @click:clear="from_date = null"
                ></v-text-field>
              </template>
              <v-date-picker
                v-model="from_date"
                @update:model-value="handleFromDateChange"
                color="primary"
              ></v-date-picker>
            </v-menu>
          </v-col>

          <v-col cols="12" md="3">
            <v-menu v-model="to_date_menu" :close-on-content-click="false" transition="scale-transition">
              <template v-slot:activator="{ props }">
                <v-text-field
                  :model-value="formatDateDisplay(to_date)"
                  :label="__('To Date')"
                  prepend-inner-icon="mdi-calendar"
                  variant="outlined"
                  density="compact"
                  readonly
                  v-bind="props"
                  clearable
                  @click:clear="to_date = null"
                ></v-text-field>
              </template>
              <v-date-picker
                v-model="to_date"
                @update:model-value="handleToDateChange"
                color="primary"
              ></v-date-picker>
            </v-menu>
          </v-col>

          <!-- Invoice Number Search -->
          <v-col cols="12" md="3">
            <v-text-field
              v-model="invoice_search"
              :label="__('Invoice Number')"
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              density="compact"
              clearable
              @keyup.enter="fetch_transactions"
            ></v-text-field>
          </v-col>

          <!-- Search Button -->
          <v-col cols="12" md="3">
            <v-btn
              color="primary"
              variant="elevated"
              block
              @click="fetch_transactions"
              :loading="loading"
            >
              <v-icon left>mdi-magnify</v-icon>
              {{ __("Search") }}
            </v-btn>
          </v-col>
        </v-row>

        <!-- Summary Cards -->
        <v-row dense class="mt-4" v-if="transactions.length > 0">
          <v-col cols="12" md="3">
            <v-card variant="outlined">
              <v-card-text class="text-center">
                <div class="text-h6">{{ transactions.length }}</div>
                <div class="text-caption">{{ __("Total Invoices") }}</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="3">
            <v-card variant="outlined">
              <v-card-text class="text-center">
                <div class="text-h6">{{ formatCurrency(total_amount) }}</div>
                <div class="text-caption">{{ __("Total Amount") }}</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="3">
            <v-card variant="outlined">
              <v-card-text class="text-center">
                <div class="text-h6">{{ formatCurrency(total_tax) }}</div>
                <div class="text-caption">{{ __("Total Tax") }}</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="3">
            <v-card variant="outlined">
              <v-card-text class="text-center">
                <div class="text-h6">{{ formatCurrency(total_discount) }}</div>
                <div class="text-caption">{{ __("Total Discount") }}</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Transactions Table -->
        <v-row class="mt-4">
          <v-col cols="12">
            <v-expansion-panels v-if="transactions.length > 0">
              <v-expansion-panel
                v-for="(transaction, index) in transactions"
                :key="index"
                class="mb-2"
              >
                <v-expansion-panel-title>
                  <v-row no-gutters align="center">
                    <v-col cols="3">
                      <v-chip color="primary" size="small">
                        {{ transaction.invoice_no }}
                      </v-chip>
                    </v-col>
                    <v-col cols="3">
                      <v-icon size="small" class="mr-1">mdi-calendar</v-icon>
                      {{ formatDate(transaction.posting_date) }}
                    </v-col>
                    <v-col cols="3">
                      <v-icon size="small" class="mr-1">mdi-account</v-icon>
                      {{ transaction.customer_name || transaction.customer }}
                    </v-col>
                    <v-col cols="3" class="text-right">
                      <strong>{{ formatCurrency(transaction.grand_total) }}</strong>
                    </v-col>
                  </v-row>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <!-- Items Table -->
                  <v-table density="compact">
                    <thead>
                      <tr>
                        <th>{{ __("Item") }}</th>
                        <th>{{ __("Item Name") }}</th>
                        <th class="text-center">{{ __("Qty") }}</th>
                        <th class="text-center">{{ __("UOM") }}</th>
                        <th class="text-right">{{ __("Rate") }}</th>
                        <th class="text-right">{{ __("Amount") }}</th>
                        <th class="text-right">{{ __("Tax") }}</th>
                        <th class="text-right">{{ __("Total") }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(item, itemIndex) in transaction.items" :key="itemIndex">
                        <td>{{ item.item_code }}</td>
                        <td>{{ item.item_name }}</td>
                        <td class="text-center">{{ item.qty }}</td>
                        <td class="text-center">{{ item.uom }}</td>
                        <td class="text-right">{{ formatCurrency(item.rate) }}</td>
                        <td class="text-right">{{ formatCurrency(item.amount) }}</td>
                        <td class="text-right">{{ formatCurrency(item.tax_amount || 0) }}</td>
                        <td class="text-right">
                          <strong>{{ formatCurrency((item.amount || 0) + (item.tax_amount || 0)) }}</strong>
                        </td>
                      </tr>
                    </tbody>
                    <tfoot>
                      <tr>
                        <td colspan="5" class="text-right"><strong>{{ __("Subtotal") }}:</strong></td>
                        <td class="text-right">
                          <strong>{{ formatCurrency(getInvoiceSubtotal(transaction)) }}</strong>
                        </td>
                        <td class="text-right">
                          <strong>{{ formatCurrency(transaction.total_taxes || 0) }}</strong>
                        </td>
                        <td class="text-right">
                          <strong>{{ formatCurrency(transaction.grand_total) }}</strong>
                        </td>
                      </tr>
                    </tfoot>
                  </v-table>

                  <!-- Tax Details -->
                  <div v-if="transaction.taxes && transaction.taxes.length > 0" class="mt-3">
                    <div class="text-subtitle-2 mb-2">{{ __("Tax Details") }}</div>
                    <v-table density="compact">
                      <thead>
                        <tr>
                          <th>{{ __("Tax Description") }}</th>
                          <th class="text-right">{{ __("Tax Amount") }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(tax, taxIndex) in transaction.taxes" :key="taxIndex">
                          <td>{{ tax.description }}</td>
                          <td class="text-right">{{ formatCurrency(tax.tax_amount) }}</td>
                        </tr>
                      </tbody>
                    </v-table>
                  </div>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <!-- No Data Message -->
            <v-alert
              v-else-if="!loading"
              type="info"
              variant="tonal"
              class="mt-4"
            >
              {{ __("No transactions found for the selected criteria") }}
            </v-alert>

            <!-- Loading State -->
            <div v-if="loading" class="text-center mt-4">
              <v-progress-circular
                indeterminate
                color="primary"
                size="64"
              ></v-progress-circular>
              <div class="mt-2">{{ __("Loading transactions...") }}</div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>

      <!-- Footer Actions -->
      <v-card-actions class="pa-4">
        <v-spacer></v-spacer>
        <v-btn
          color="primary"
          variant="outlined"
          @click="export_to_excel"
          :disabled="transactions.length === 0"
        >
          <v-icon left>mdi-microsoft-excel</v-icon>
          {{ __("Export to Excel") }}
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="close_dialog"
        >
          {{ __("Close") }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import format from "../../format";

export default {
  mixins: [format],
  data() {
    return {
      dialog: false,
      loading: false,
      from_date: null,
      to_date: null,
      from_date_menu: false,
      to_date_menu: false,
      invoice_search: "",
      transactions: [],
      pos_profile: null,
      customer: null,
    };
  },

  computed: {
    total_amount() {
      return this.transactions.reduce((sum, t) => sum + (t.grand_total || 0), 0);
    },
    total_tax() {
      return this.transactions.reduce((sum, t) => sum + (t.total_taxes || 0), 0);
    },
    total_discount() {
      return this.transactions.reduce((sum, t) => sum + (t.discount_amount || 0), 0);
    },
  },

  methods: {
    open_dialog() {
      this.dialog = true;
      // Set default date range (last 7 days) using Frappe's date functions
      const today = frappe.datetime.nowdate(); // Returns YYYY-MM-DD string
      const sevenDaysAgo = frappe.datetime.add_days(today, -7); // Returns YYYY-MM-DD string
      
      // Keep dates as strings in YYYY-MM-DD format
      this.to_date = today;
      this.from_date = sevenDaysAgo;
      
      this.fetch_transactions();
    },

    close_dialog() {
      this.dialog = false;
      this.transactions = [];
      this.invoice_search = "";
    },

    async fetch_transactions() {
      this.loading = true;
      try {
        // Convert dates to YYYY-MM-DD format if they exist
        let formatted_from_date = null;
        let formatted_to_date = null;
        
        if (this.from_date) {
          // Check if it's a Date object or string
          if (this.from_date instanceof Date) {
            formatted_from_date = this.formatDateForAPI(this.from_date);
          } else if (typeof this.from_date === 'string') {
            // If it's already a string, try to parse and format it
            const date = new Date(this.from_date);
            if (!isNaN(date)) {
              formatted_from_date = this.formatDateForAPI(date);
            } else {
              formatted_from_date = this.from_date; // Use as-is if can't parse
            }
          }
        }
        
        if (this.to_date) {
          // Check if it's a Date object or string
          if (this.to_date instanceof Date) {
            formatted_to_date = this.formatDateForAPI(this.to_date);
          } else if (typeof this.to_date === 'string') {
            // If it's already a string, try to parse and format it
            const date = new Date(this.to_date);
            if (!isNaN(date)) {
              formatted_to_date = this.formatDateForAPI(date);
            } else {
              formatted_to_date = this.to_date; // Use as-is if can't parse
            }
          }
        }
        
        const response = await frappe.call({
          method: "posawesome.posawesome.api.posapp.get_all_previous_transactions",
          args: {
            from_date: formatted_from_date,
            to_date: formatted_to_date,
            customer: this.customer,
            invoice_no: this.invoice_search,
            pos_profile: this.pos_profile?.name,
            limit: 100,
          },
        });

        if (response.message) {
          this.transactions = response.message;
        } else {
          this.transactions = [];
        }
      } catch (error) {
        console.error("Error fetching transactions:", error);
        this.eventBus.emit("show_message", {
          title: __("Error fetching transactions"),
          color: "error",
        });
        this.transactions = [];
      } finally {
        this.loading = false;
      }
    },

    getInvoiceSubtotal(transaction) {
      if (!transaction.items) return 0;
      return transaction.items.reduce((sum, item) => sum + (item.amount || 0), 0);
    },

    formatDate(date) {
      if (!date) return "";
      return frappe.datetime.str_to_user(date);
    },

    formatCurrency(value) {
      if (!value && value !== 0) return "0.00";
      return format_currency(value, this.pos_profile?.currency || "USD");
    },
    
    formatDateForAPI(date) {
      // Convert Date object to YYYY-MM-DD format
      if (!date) return null;
      
      let d = date;
      if (typeof date === 'string') {
        d = new Date(date);
      }
      
      if (!(d instanceof Date) || isNaN(d)) {
        return null;
      }
      
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      
      return `${year}-${month}-${day}`;
    },
    
    formatDateDisplay(date) {
      // Format date for display in the text field
      if (!date) return '';
      
      // If it's already in YYYY-MM-DD format, convert to user format
      if (typeof date === 'string' && date.match(/^\d{4}-\d{2}-\d{2}$/)) {
        return frappe.datetime.str_to_user(date);
      }
      
      // If it's a Date object, format it
      if (date instanceof Date && !isNaN(date)) {
        const formatted = this.formatDateForAPI(date);
        return frappe.datetime.str_to_user(formatted);
      }
      
      return date;
    },
    
    handleFromDateChange(value) {
      // Handle date change from date picker
      if (value) {
        // If value is a Date object, convert to YYYY-MM-DD string
        if (value instanceof Date) {
          this.from_date = this.formatDateForAPI(value);
        } else {
          this.from_date = value;
        }
      }
      this.from_date_menu = false;
    },
    
    handleToDateChange(value) {
      // Handle date change from date picker
      if (value) {
        // If value is a Date object, convert to YYYY-MM-DD string
        if (value instanceof Date) {
          this.to_date = this.formatDateForAPI(value);
        } else {
          this.to_date = value;
        }
      }
      this.to_date_menu = false;
    },

    export_to_excel() {
      // Create CSV content
      let csv = "Invoice No,Date,Customer,Item Code,Item Name,Qty,UOM,Rate,Amount,Tax,Total\n";
      
      this.transactions.forEach(transaction => {
        transaction.items.forEach(item => {
          const total = (item.amount || 0) + (item.tax_amount || 0);
          csv += `"${transaction.invoice_no}","${this.formatDate(transaction.posting_date)}","${transaction.customer_name || transaction.customer}","${item.item_code}","${item.item_name}",${item.qty},"${item.uom}",${item.rate},${item.amount},${item.tax_amount || 0},${total}\n`;
        });
      });

      // Create download link
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);
      link.setAttribute("href", url);
      link.setAttribute("download", `transactions_${frappe.datetime.nowdate()}.csv`);
      link.style.visibility = "hidden";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      this.eventBus.emit("show_message", {
        title: __("Transactions exported successfully"),
        color: "success",
      });
    },
  },

  mounted() {
    this.eventBus.on("open_previous_transactions", (data) => {
      this.pos_profile = data.pos_profile;
      this.customer = data.customer;
      this.open_dialog();
    });

    this.eventBus.on("register_pos_profile", (data) => {
      this.pos_profile = data.pos_profile;
    });

    this.eventBus.on("update_customer", (customer) => {
      this.customer = customer;
    });
  },

  beforeUnmount() {
    this.eventBus.off("open_previous_transactions");
    this.eventBus.off("register_pos_profile");
    this.eventBus.off("update_customer");
  },
};
</script>

<style scoped>
.v-expansion-panel-title {
  padding: 12px 16px;
}

.v-expansion-panel-text {
  padding: 16px;
}

.v-table {
  background-color: #f5f5f5;
}

.v-table thead th {
  background-color: #e0e0e0;
  font-weight: 600;
}

.v-table tfoot td {
  background-color: #eeeeee;
  font-weight: 600;
}
</style>